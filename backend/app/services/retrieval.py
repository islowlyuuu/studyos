from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import SessionLocal
from app.llm.embeddings import embed_text
from app.models import DocumentChunk, SourceDocument


def retrieve(query: str, top_k: int | None = None, user_id: int | None = None) -> list[tuple[DocumentChunk, float]]:
    """向量检索，返回 [(片段, 余弦距离)]，按距离升序。"""
    k = top_k or settings.vector_top_k
    qvec = embed_text(query)
    dist = DocumentChunk.embedding.cosine_distance(qvec)

    db = SessionLocal()
    try:
        stmt = (
            select(DocumentChunk, dist)
            .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
            .options(selectinload(DocumentChunk.document))
            .order_by(dist)
            .limit(k)
        )
        if user_id is not None:
            stmt = stmt.where(SourceDocument.user_id == user_id)
        rows = db.execute(stmt).all()
        return [(chunk, float(d)) for chunk, d in rows]
    finally:
        db.close()
