"""工具注册表：每个工具定义参数 JSON Schema（给模型）+ Pydantic 模型（本地校验）+ 执行函数（持久化）。"""
import json

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.database import SessionLocal
from app.llm.client import chat_json
from app.models import KnowledgePoint, MistakeRecord, StudyPlan

VALID_MASTERY = ["new", "learning", "familiar", "mastered", "needs_review"]


class RecordMistakeArgs(BaseModel):
    question: str
    knowledge_points: list[str] = Field(min_length=1)
    note: str = ""


class UpdateMasteryArgs(BaseModel):
    knowledge_point: str
    mastery_level: str


class CreateStudyPlanArgs(BaseModel):
    goal: str
    focus_points: list[str] = Field(default_factory=list)
    duration_days: int = Field(default=7, ge=1, le=30)


def _upsert_knowledge_point(db, user_id: int, name: str, mastery_level: str = "needs_review"):
    kp = db.execute(
        select(KnowledgePoint).where(KnowledgePoint.user_id == user_id, KnowledgePoint.name == name)
    ).scalars().first()
    if kp is None:
        kp = KnowledgePoint(user_id=user_id, name=name)
        db.add(kp)
    kp.mastery_level = mastery_level
    return kp


def record_mistake(user_id: int, args: RecordMistakeArgs) -> str:
    db = SessionLocal()
    try:
        for kp_name in args.knowledge_points:
            _upsert_knowledge_point(db, user_id, kp_name, "needs_review")
        rec = MistakeRecord(
            user_id=user_id,
            question=args.question,
            knowledge_points=args.knowledge_points,
            note=args.note,
        )
        db.add(rec)
        db.commit()
        return json.dumps(
            {"ok": True, "mistake_id": rec.id, "knowledge_points": args.knowledge_points},
            ensure_ascii=False,
        )
    finally:
        db.close()


def update_mastery(user_id: int, args: UpdateMasteryArgs) -> str:
    if args.mastery_level not in VALID_MASTERY:
        return json.dumps(
            {"ok": False, "error": f"mastery_level 必须是 {VALID_MASTERY} 之一，收到 {args.mastery_level}"},
            ensure_ascii=False,
        )
    db = SessionLocal()
    try:
        kp = _upsert_knowledge_point(db, user_id, args.knowledge_point, args.mastery_level)
        db.commit()
        return json.dumps(
            {"ok": True, "knowledge_point": kp.name, "mastery_level": kp.mastery_level},
            ensure_ascii=False,
        )
    finally:
        db.close()


def create_study_plan(user_id: int, args: CreateStudyPlanArgs) -> str:
    prompt = (
        "你是学习规划师。为一个学习目标制定每日学习计划。\n"
        f"目标：{args.goal}\n"
        f"重点内容：{', '.join(args.focus_points) if args.focus_points else '无'}\n"
        f"时长：{args.duration_days} 天\n"
        "请输出 JSON，包含每天的安排：\n"
        '{"days": [{"day": 1, "content": "..."}]}'
    )
    text = chat_json([{"role": "user", "content": prompt}], temperature=0.5)
    db = SessionLocal()
    try:
        plan = StudyPlan(
            user_id=user_id,
            goal=args.goal,
            focus_points=args.focus_points,
            duration_days=args.duration_days,
            content=text,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return json.dumps(
            {"ok": True, "plan_id": plan.id, "duration_days": plan.duration_days, "content": text},
            ensure_ascii=False,
        )
    finally:
        db.close()


TOOL_REGISTRY = {
    "record_mistake": {
        "description": "记录一道错题及其涉及的薄弱知识点，用于后续复习",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "错题的题干或描述"},
                "knowledge_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "这道错题涉及的薄弱知识点",
                },
                "note": {"type": "string", "description": "可选备注"},
            },
            "required": ["question", "knowledge_points"],
        },
        "args_model": RecordMistakeArgs,
        "handler": record_mistake,
    },
    "update_mastery": {
        "description": "更新某个知识点的掌握度（new/learning/familiar/mastered/needs_review）",
        "parameters": {
            "type": "object",
            "properties": {
                "knowledge_point": {"type": "string", "description": "知识点名称"},
                "mastery_level": {
                    "type": "string",
                    "enum": VALID_MASTERY,
                    "description": "新的掌握度",
                },
            },
            "required": ["knowledge_point", "mastery_level"],
        },
        "args_model": UpdateMasteryArgs,
        "handler": update_mastery,
    },
    "create_study_plan": {
        "description": "根据学习目标生成一份每日学习计划",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "学习目标"},
                "focus_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "重点学习的内容",
                },
                "duration_days": {"type": "integer", "description": "计划天数，默认 7"},
            },
            "required": ["goal"],
        },
        "args_model": CreateStudyPlanArgs,
        "handler": create_study_plan,
    },
}


def tools_spec() -> list[dict]:
    """返回给模型的 OpenAI 格式工具定义。"""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
        }
        for name, spec in TOOL_REGISTRY.items()
    ]


def execute_tool(name: str, args: dict, user_id: int) -> tuple[bool, str]:
    """执行工具；参数校验失败时返回错误且不产生副作用。"""
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return False, f"未知工具: {name}"
    try:
        validated = spec["args_model"](**args)
    except Exception as e:
        return False, f"参数校验失败: {e}"
    try:
        output = spec["handler"](user_id, validated)
    except Exception as e:
        return False, f"工具执行失败: {e}"
    return True, output
