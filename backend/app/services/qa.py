import hashlib
import json

from app.config import settings
from app.llm.client import chat, stream_chat
from app.services.queue import get_redis
from app.services.retrieval import retrieve
from app.services.governance import cache_namespace

CACHE_PREFIX = "studyos:qa:"


def _cache_key(query: str, user_id: int | None) -> str:
    normalized = " ".join(query.split())
    return f"{CACHE_PREFIX}{cache_namespace(user_id or 1)}:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _similarity(distance: float) -> float:
    return 1.0 - distance  # 向量已归一化，余弦距离 = 1 - 余弦相似度


def _sources(chunks):
    sources = []
    for i, chunk in enumerate(chunks, start=1):
        sources.append(
            {
                "index": i,
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "heading_path": chunk.heading_path,
                "page_number": chunk.page_number,
                "filename": chunk.document.filename if chunk.document else "",
            }
        )
    return sources


def _prompt_for(query: str, chunks) -> tuple[list[dict], str]:
    context = "\n\n".join(f"[{i}] {c.content}" for i, c in enumerate(chunks, start=1))
    system = (
        "你是一个严谨的学习助手。只依据下方提供的资料回答用户问题。"
        "回答中的每个关键结论后面用 [编号] 标注资料来源。"
        "如果资料不足以回答，明确说明证据不足，不要编造。"
    )
    user = f"资料：\n{context}\n\n问题：{query}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}], context


def _insufficient() -> dict:
    return {
        "answer": "证据不足：知识库里没有足够相关的内容来回答这个问题。你可以先导入相关学习资料，或换个问题。",
        "sources": [],
        "sufficient": False,
        "latency_ms": 0,
        "cached": False,
    }


def answer_question(query: str, user_id: int | None = None) -> dict:
    r = get_redis()
    key = _cache_key(query, user_id)
    cached = r.get(key)
    if cached:
        data = json.loads(cached)
        data["cached"] = True
        return data

    hits = retrieve(query, user_id=user_id)
    chunks = [c for c, _ in hits]

    if not chunks or _similarity(hits[0][1]) < settings.min_similarity:
        result = _insufficient()
        r.setex(key, settings.cache_ttl_seconds, json.dumps(result, ensure_ascii=False))
        return result

    messages, _ = _prompt_for(query, chunks)
    resp, latency = chat(messages, temperature=0.3)
    result = {
        "answer": resp.choices[0].message.content,
        "sources": _sources(chunks),
        "sufficient": True,
        "latency_ms": latency,
        "cached": False,
    }
    r.setex(key, settings.cache_ttl_seconds, json.dumps(result, ensure_ascii=False))
    return result


def stream_answer(query: str, user_id: int | None = None):
    """SSE 生成器：先发 meta（来源），再逐段发 delta，最后发 done。"""
    r = get_redis()
    key = _cache_key(query, user_id)

    cached = r.get(key)
    if cached:
        data = json.loads(cached)
        yield _sse({"type": "meta", "sources": data["sources"], "sufficient": data["sufficient"], "cached": True})
        yield _sse({"type": "delta", "text": data["answer"]})
        yield _sse({"type": "done"})
        return

    hits = retrieve(query, user_id=user_id)
    chunks = [c for c, _ in hits]

    if not chunks or _similarity(hits[0][1]) < settings.min_similarity:
        data = _insufficient()
        r.setex(key, settings.cache_ttl_seconds, json.dumps(data, ensure_ascii=False))
        yield _sse({"type": "meta", "sources": [], "sufficient": False, "cached": False})
        yield _sse({"type": "delta", "text": data["answer"]})
        yield _sse({"type": "done"})
        return

    sources = _sources(chunks)
    yield _sse({"type": "meta", "sources": sources, "sufficient": True, "cached": False})

    messages, _ = _prompt_for(query, chunks)
    parts = []
    for text in stream_chat(messages, temperature=0.3):
        parts.append(text)
        yield _sse({"type": "delta", "text": text})

    answer = "".join(parts)
    r.setex(key, settings.cache_ttl_seconds, json.dumps(
        {"answer": answer, "sources": sources, "sufficient": True, "latency_ms": 0, "cached": False},
        ensure_ascii=False,
    ))
    yield _sse({"type": "done"})


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
