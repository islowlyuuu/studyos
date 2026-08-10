import json
import re

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.llm.client import chat_json
from app.models import AnswerAttempt, KnowledgePoint, Question
from app.services.retrieval import retrieve

QUESTION_SCHEMA = """{
  "question_type": "short_answer | single_choice | true_false",
  "difficulty": "easy | medium | hard",
  "content": "题面文字",
  "options": ["选项A", "选项B", "..."] 或 null,
  "reference_answer": "参考答案（简答给要点；选择给正确选项和理由）",
  "rubric": {"dimensions": [{"name": "维度名", "weight": 0.4, "description": "怎么算分"}]},
  "knowledge_points": ["知识点1", "知识点2"],
  "source_indices": [1, 3]
}"""

GRADE_SCHEMA = """{
  "score": 0,
  "dimensions": [{"name": "维度名", "score": 80, "comment": "该维度点评"}],
  "feedback": "总评，指出主要问题与改进方向",
  "mistakes": ["薄弱知识点1", "薄弱知识点2"],
  "suggested_review": ["建议复习的要点"]
}"""


def _parse_json(text: str) -> dict:
    """解析模型输出的 JSON，容忍可能的 ```json 包裹。"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def generate_question(topic: str, user_id: int, question_type: str | None = None) -> dict:
    """基于知识库生成一道题，题目必须绑定来源片段与知识点。"""
    hits = retrieve(topic, top_k=6, user_id=user_id)
    if not hits:
        return {"error": "知识库为空或检索不到相关内容，请先导入资料。"}

    chunks = [c for c, _ in hits]
    context = "\n\n".join(f"[{i}] {c.content}" for i, c in enumerate(chunks, start=1))
    type_hint = f"，题型限定为 {question_type}" if question_type else ""
    prompt = (
        f"你是一名出题老师。请依据下方知识库资料{type_hint}出一道练习题。\n"
        "要求：\n"
        "- 题目必须完全基于资料内容，不得脱离资料出题\n"
        "- reference_answer 给出答题要点；选择题给出正确选项和理由\n"
        "- rubric 按 2-3 个维度设计评分规则，weight 之和为 1\n"
        "- source_indices 填写题目依据的资料编号（必须是上面给出的编号）\n"
        "- knowledge_points 概括题目考察的知识点\n\n"
        f"资料：\n{context}\n\n"
        f"请输出 JSON：\n{QUESTION_SCHEMA}"
    )
    text = chat_json([{"role": "user", "content": prompt}], temperature=0.7)
    data = _parse_json(text)

    source_chunk_ids = []
    for idx in data.get("source_indices", []):
        if 1 <= idx <= len(chunks):
            source_chunk_ids.append(chunks[idx - 1].id)

    db = SessionLocal()
    try:
        q = Question(
            user_id=user_id,
            question_type=data.get("question_type", "short_answer"),
            difficulty=data.get("difficulty", "medium"),
            content=data.get("content", ""),
            reference_answer=data.get("reference_answer", ""),
            rubric=data.get("rubric", {}),
            source_chunk_ids=source_chunk_ids,
            knowledge_point_ids=data.get("knowledge_points", []),
        )
        db.add(q)
        db.commit()
        db.refresh(q)
    finally:
        db.close()

    return {
        "id": q.id,
        "question_type": q.question_type,
        "difficulty": q.difficulty,
        "content": q.content,
        "options": data.get("options"),
        "knowledge_points": data.get("knowledge_points", []),
        "source_chunk_ids": source_chunk_ids,
    }


def grade_answer(question_id: int, answer: str, user_id: int) -> dict:
    """按评分规则结构化批改，得分低于阈值时记录错题与薄弱知识点。"""
    db = SessionLocal()
    try:
        q = db.get(Question, question_id)
        if q is None:
            return {"error": "题目不存在"}

        rubric = q.rubric or {}
        prompt = (
            "你是一名严格的批改老师。请按评分规则对学生的答案打分。\n\n"
            f"题目：{q.content}\n"
            f"参考答案：{q.reference_answer}\n"
            f"评分规则：{json.dumps(rubric, ensure_ascii=False)}\n"
            f"学生答案：{answer}\n\n"
            f"请输出 JSON：\n{GRADE_SCHEMA}"
        )
        text = chat_json([{"role": "user", "content": prompt}], temperature=0.2)
        data = _parse_json(text)

        score = float(data.get("score", 0))
        attempt = AnswerAttempt(
            question_id=question_id,
            user_id=user_id,
            answer=answer,
            score=score,
            feedback=data.get("feedback", ""),
            mistakes=data.get("mistakes", []),
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        weak = score < settings.score_threshold
        if weak:
            for kp in q.knowledge_point_ids:
                _mark_weak(db, user_id, str(kp))
            for m in data.get("mistakes", []):
                _mark_weak(db, user_id, str(m))

        return {
            "attempt_id": attempt.id,
            "score": score,
            "dimensions": data.get("dimensions", []),
            "feedback": data.get("feedback", ""),
            "mistakes": data.get("mistakes", []),
            "suggested_review": data.get("suggested_review", []),
            "passed": not weak,
        }
    finally:
        db.close()


def _mark_weak(db, user_id: int, name: str) -> None:
    """把知识点标记为 needs_review；不存在则新建。"""
    kp = db.execute(
        select(KnowledgePoint).where(KnowledgePoint.user_id == user_id, KnowledgePoint.name == name)
    ).scalars().first()
    if kp is None:
        kp = KnowledgePoint(user_id=user_id, name=name)
        db.add(kp)
    kp.mastery_level = "needs_review"
    db.commit()
