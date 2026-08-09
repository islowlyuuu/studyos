from app.database import SessionLocal
from app.llm.embeddings import embed_texts
from app.models import DocumentChunk, SourceDocument
from app.services.chunker import chunk_document
from app.services.parser import parse_document


def ingest_document(doc_id: int, filename: str, data: bytes, file_type: str) -> None:
    """解析 → 分块 → 向量化 → 入库。由后台 worker 调用。"""
    db = SessionLocal()
    try:
        doc = db.get(SourceDocument, doc_id)
        if doc is None:
            return
        doc.parse_status = "parsing"
        db.commit()

        pages = parse_document(filename, data, file_type)
        chunks = chunk_document(pages)

        vectors = embed_texts([c.content for c in chunks])

        for chunk, vec in zip(chunks, vectors):
            db.add(
                DocumentChunk(
                    document_id=doc_id,
                    content=chunk.content,
                    heading_path=chunk.heading_path,
                    page_number=chunk.page_number,
                    embedding=vec,
                )
            )
        doc.parse_status = "done"
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
