import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from app.database import SessionLocal
from app.models import SourceDocument
from app.services.queue import enqueue_parse

router = APIRouter(prefix="/api/documents", tags=["documents"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")

SUPPORTED_TYPES = {
    "md", "markdown", "txt", "pdf",
    "py", "js", "ts", "tsx", "java", "go", "rs", "c", "cpp",
    "html", "css", "json", "yaml", "yml", "sql",
}

DEFAULT_USER_ID = 1


@router.post("")
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename or "untitled"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.{ext}")
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    db = SessionLocal()
    try:
        doc = SourceDocument(
            user_id=DEFAULT_USER_ID,
            filename=filename,
            file_type=ext,
            storage_path=save_path,
            parse_status="pending",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
    finally:
        db.close()

    enqueue_parse(doc.id, save_path, filename, ext)
    return {"id": doc.id, "filename": filename, "status": "pending"}


@router.get("")
def list_documents():
    db = SessionLocal()
    try:
        docs = db.execute(select(SourceDocument).order_by(SourceDocument.id.desc())).scalars().all()
        return [
            {"id": d.id, "filename": d.filename, "file_type": d.file_type, "parse_status": d.parse_status}
            for d in docs
        ]
    finally:
        db.close()
