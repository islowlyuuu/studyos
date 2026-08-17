from datetime import datetime, timezone

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import KnowledgeBaseState, SourceDocument


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_generation(user_id: int) -> int:
    db = SessionLocal()
    try:
        state = db.execute(select(KnowledgeBaseState).where(KnowledgeBaseState.user_id == user_id)).scalars().first()
        if state is None:
            state = KnowledgeBaseState(user_id=user_id, generation=1)
            db.add(state)
            db.commit()
        return state.generation
    finally:
        db.close()


def bump_generation(db, user_id: int) -> int:
    state = db.execute(select(KnowledgeBaseState).where(KnowledgeBaseState.user_id == user_id)).scalars().first()
    if state is None:
        state = KnowledgeBaseState(user_id=user_id, generation=2)
        db.add(state)
    else:
        state.generation += 1
        state.updated_at = _now()
    return state.generation


def cache_namespace(user_id: int) -> str:
    return f"u{user_id}:g{get_generation(user_id)}:k{settings.vector_top_k}:e{settings.embedding_model}"


def document_payload(document: SourceDocument) -> dict:
    return {
        "id": document.id,
        "logical_key": document.logical_key,
        "version": document.version,
        "filename": document.filename,
        "file_type": document.file_type,
        "parse_status": document.parse_status,
        "is_active": document.is_active,
        "cancel_requested": document.cancel_requested,
        "content_hash": document.content_hash,
        "parser_version": document.parser_version,
        "chunker_version": document.chunker_version,
        "embedding_model": document.embedding_model,
        "indexed_at": document.indexed_at.isoformat() if document.indexed_at else None,
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }
