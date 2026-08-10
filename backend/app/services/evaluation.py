"""评测：召回质量（Recall@K / MRR）与带引用问答的引用正确性/完整性。"""
import re

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import DocumentChunk, SourceDocument
from app.services.retrieval import retrieve

CITE_RE = re.compile(r"\[(\d+)\]")


def recall_at_k(predicted_ids: list[int], relevant_ids: set[int], k: int) -> float:
    if not relevant_ids:
        return 0.0
    hit = set(predicted_ids[:k]) & relevant_ids
    return len(hit) / len(relevant_ids)


def mrr(predicted_ids: list[int], relevant_ids: set[int]) -> float:
    relevant = set(relevant_ids)
    for i, pid in enumerate(predicted_ids, start=1):
        if pid in relevant:
            return 1.0 / i
    return 0.0


def _all_chunks(user_id: int) -> list[tuple[DocumentChunk, str]]:
    db = SessionLocal()
    try:
        stmt = (
            select(DocumentChunk, SourceDocument.filename)
            .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
            .where(SourceDocument.user_id == user_id)
        )
        return [(c, fn) for c, fn in db.execute(stmt)]
    finally:
        db.close()


def _match_keywords(content: str, filename: str, keywords: list[str]) -> bool:
    haystack = f"{content} {filename}".lower()
    return all(kw.lower() in haystack for kw in keywords)


def evaluate_retrieval(eval_set: list[dict], user_id: int) -> dict:
    """对每道题做检索，按人工标注的"来源关键词"判定相关片段，算 Recall@K 与 MRR。"""
    k = settings.eval_top_k
    all_chunks = _all_chunks(user_id)
    by_id = {c.id: (c, fn) for c, fn in all_chunks}

    rows = []
    for item in eval_set:
        hits = retrieve(item["question"], top_k=k, user_id=user_id)
        predicted_ids = [c.id for c, _ in hits]

        relevant_ids = {
            cid
            for cid, (c, fn) in by_id.items()
            if _match_keywords(c.content, fn, item["expected_source_keywords"])
        }

        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "recall_at_k": recall_at_k(predicted_ids, relevant_ids, k),
                "mrr": mrr(predicted_ids, relevant_ids),
                "n_relevant": len(relevant_ids),
                "k": k,
            }
        )

    recall = sum(r["recall_at_k"] for r in rows) / len(rows) if rows else 0.0
    avg_mrr = sum(r["mrr"] for r in rows) / len(rows) if rows else 0.0
    return {"rows": rows, "avg_recall_at_k": recall, "avg_mrr": avg_mrr}


def evaluate_citations(eval_set: list[dict], user_id: int) -> dict:
    """跑带引用问答，检查引用编号是否有效（正确性）与关键答案要点是否覆盖（完整性）。"""
    from app.services.qa import answer_question

    rows = []
    for item in eval_set:
        ans = answer_question(item["question"], user_id=user_id)
        text = ans["answer"] or ""
        n_sources = len(ans["sources"])

        cited = [int(m) for m in CITE_RE.findall(text)]
        valid = [i for i in cited if 1 <= i <= n_sources]
        correctness = len(valid) / len(cited) if cited else 0.0

        key_points = item.get("key_answer_points", [])
        missing = [kp for kp in key_points if kp.lower() not in text.lower()]
        completeness = 1.0 - len(missing) / len(key_points) if key_points else 1.0

        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "cited": cited,
                "citation_correctness": correctness,
                "completeness": completeness,
                "missing_key_points": missing,
                "sufficient": ans.get("sufficient", False),
            }
        )

    correctness = sum(r["citation_correctness"] for r in rows) / len(rows) if rows else 0.0
    completeness = sum(r["completeness"] for r in rows) / len(rows) if rows else 0.0
    return {
        "rows": rows,
        "avg_citation_correctness": correctness,
        "avg_completeness": completeness,
    }
