"""评测：召回质量（Recall@K / MRR）与带引用问答的引用正确性/完整性。"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import DocumentChunk, EvaluationRun, SourceDocument
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
            .where(SourceDocument.user_id == user_id, SourceDocument.parse_status == "done", SourceDocument.is_active.is_(True), SourceDocument.cancel_requested.is_(False))
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


CORPUS_REQUIRED_FIELDS = {
    "id", "question", "topic", "expected_logical_key", "expected_version",
    "expected_chunk_ids", "expected_source", "key_answer_points",
    "forbidden_conclusions", "reviewed_by", "reviewed_at",
}


def load_corpus_eval(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def validate_corpus_eval(dataset: dict, user_id: int) -> dict:
    items = dataset.get("items", [])
    errors: list[str] = []
    coverage = {"formats": set(), "topics": set(), "documents": set()}
    db = SessionLocal()
    try:
        for index, item in enumerate(items, start=1):
            missing = sorted(CORPUS_REQUIRED_FIELDS - set(item))
            if missing:
                errors.append(f"item {index}: ???? {', '.join(missing)}")
                continue
            document = db.execute(select(SourceDocument).where(
                SourceDocument.user_id == user_id,
                SourceDocument.logical_key == item["expected_logical_key"],
                SourceDocument.version == item["expected_version"],
                SourceDocument.is_active.is_(True),
                SourceDocument.parse_status == "done",
                SourceDocument.cancel_requested.is_(False),
            )).scalars().first()
            if document is None:
                errors.append(f"item {item['id']}: ???????????????????")
                continue
            actual_chunk_ids = {chunk.id for chunk in document.chunks}
            unknown = set(item["expected_chunk_ids"]) - actual_chunk_ids
            if unknown:
                errors.append(f"item {item['id']}: ?????? {sorted(unknown)}")
            coverage["formats"].add(document.file_type)
            coverage["topics"].add(item["topic"])
            coverage["documents"].add(document.id)
    finally:
        db.close()

    readiness_errors = []
    if len(items) < 20:
        readiness_errors.append(f"???????? 20 ????? {len(items)}")
    if not coverage["documents"]:
        readiness_errors.append("????????????")
    return {
        "valid": not errors,
        "ready": not errors and not readiness_errors,
        "errors": errors,
        "readiness_errors": readiness_errors,
        "coverage": {key: sorted(value) for key, value in coverage.items()},
        "count": len(items),
    }


def _corpus_snapshot(user_id: int) -> dict:
    db = SessionLocal()
    try:
        documents = db.execute(select(SourceDocument).where(
            SourceDocument.user_id == user_id,
            SourceDocument.is_active.is_(True),
            SourceDocument.parse_status == "done",
            SourceDocument.cancel_requested.is_(False),
        )).scalars().all()
        return {"created_at": datetime.now(timezone.utc).isoformat(), "documents": [
            {"id": document.id, "logical_key": document.logical_key, "version": document.version,
             "content_hash": document.content_hash, "file_type": document.file_type}
            for document in documents
        ]}
    finally:
        db.close()


def evaluate_real_corpus(dataset: dict, user_id: int) -> dict:
    validation = validate_corpus_eval(dataset, user_id)
    if not validation["ready"]:
        return {"status": "not_ready", "validation": validation, "rows": []}

    from app.services.qa import answer_question

    rows = []
    k = settings.eval_top_k
    for item in dataset["items"]:
        expected = set(item["expected_chunk_ids"])
        hits = retrieve(item["question"], top_k=k, user_id=user_id)
        predicted = [chunk.id for chunk, _ in hits]
        retrieved = set(predicted) & expected
        if not retrieved:
            failure = "not_retrieved"
        elif predicted.index(next(chunk_id for chunk_id in predicted if chunk_id in expected)) + 1 > 1:
            failure = "ranked_below_first"
        else:
            failure = None

        answer = answer_question(item["question"], user_id=user_id)
        cited_indices = [int(match) for match in CITE_RE.findall(answer.get("answer", ""))]
        sources = answer.get("sources", [])
        cited_sources = [sources[index - 1] for index in cited_indices if 1 <= index <= len(sources)]
        cited_chunk_ids = {source["chunk_id"] for source in cited_sources}
        citation_correctness = len(cited_chunk_ids & expected) / len(cited_chunk_ids) if cited_chunk_ids else 0.0
        missing_points = [point for point in item["key_answer_points"] if point.lower() not in answer.get("answer", "").lower()]
        forbidden = [claim for claim in item["forbidden_conclusions"] if claim.lower() in answer.get("answer", "").lower()]
        completeness = 1 - len(missing_points) / len(item["key_answer_points"]) if item["key_answer_points"] else 1.0
        if forbidden:
            failure = failure or "forbidden_conclusion"
        elif cited_indices and citation_correctness == 0:
            failure = failure or "wrong_citation"
        elif missing_points:
            failure = failure or "incomplete_answer"
        rows.append({
            "id": item["id"], "question": item["question"], "topic": item["topic"],
            "recall_at_k": recall_at_k(predicted, expected, k), "mrr": mrr(predicted, expected),
            "citation_correctness": citation_correctness, "citation_completeness": completeness,
            "failure": failure, "expected_chunk_ids": sorted(expected), "retrieved_chunk_ids": predicted,
            "cited_chunk_ids": sorted(cited_chunk_ids), "missing_key_points": missing_points,
            "forbidden_conclusions": forbidden,
        })

    report = {
        "status": "completed", "validation": validation, "rows": rows,
        "avg_recall_at_k": sum(row["recall_at_k"] for row in rows) / len(rows),
        "avg_mrr": sum(row["mrr"] for row in rows) / len(rows),
        "avg_citation_correctness": sum(row["citation_correctness"] for row in rows) / len(rows),
        "avg_citation_completeness": sum(row["citation_completeness"] for row in rows) / len(rows),
    }
    db = SessionLocal()
    try:
        run = EvaluationRun(
            user_id=user_id,
            dataset_version=str(dataset.get("version", "unversioned")),
            corpus_snapshot=_corpus_snapshot(user_id),
            retrieval_config={"top_k": k, "embedding_model": settings.embedding_model},
            report=report,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        report["run_id"] = run.id
    finally:
        db.close()
    return report
