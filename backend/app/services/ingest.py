from datetime import datetime, timezone

from app.config import settings
from app.database import SessionLocal
from app.llm.embeddings import embed_texts
from app.models import DocumentChunk, SourceDocument
from app.services.chunker import chunk_document
from app.services.governance import bump_generation
from app.services.parser import parse_document


def ingest_document(doc_id: int, filename: str, data: bytes, file_type: str) -> None:
    """解析 → 分块 → 向量化 → 入库；只激活仍有效的版本。"""
    db = SessionLocal()
    try:
        doc = db.get(SourceDocument, doc_id)
        if doc is None or doc.cancel_requested:
            return
        doc.parse_status = "parsing"
        db.commit()

        pages = parse_document(filename, data, file_type)
        chunks = chunk_document(pages)
        vectors = embed_texts([chunk.content for chunk in chunks])

        db.refresh(doc)
        if doc.cancel_requested:
            doc.parse_status = "cancelled"
            db.commit()
            return

        for chunk, vector in zip(chunks, vectors):
            db.add(DocumentChunk(
                document_id=doc.id,
                content=chunk.content,
                heading_path=chunk.heading_path,
                page_number=chunk.page_number,
                char_start=getattr(chunk, "char_start", None),
                char_end=getattr(chunk, "char_end", None),
                embedding=vector,
            ))

        previous = (
            db.query(SourceDocument)
            .filter(
                SourceDocument.user_id == doc.user_id,
                SourceDocument.logical_key == doc.logical_key,
                SourceDocument.id != doc.id,
                SourceDocument.is_active.is_(True),
            )
            .all()
        )
        for old in previous:
            old.is_active = False
        doc.is_active = True
        doc.parse_status = "done"
        doc.embedding_model = settings.embedding_model
        doc.indexed_at = datetime.now(timezone.utc)
        bump_generation(db, doc.user_id)
        db.commit()
    except Exception:
        db.rollback()
        doc = db.get(SourceDocument, doc_id)
        if doc is not None:
            doc.parse_status = "failed"
            db.commit()
        raise
    finally:
        db.close()
