import hashlib
import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from app.database import SessionLocal
from app.models import SourceDocument
from app.services.governance import bump_generation, document_payload
from app.services.queue import enqueue_parse

router = APIRouter(prefix="/api/documents", tags=["documents"])
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
SUPPORTED_TYPES = {"md", "markdown", "txt", "pdf", "py", "js", "ts", "tsx", "java", "go", "rs", "c", "cpp", "html", "css", "json", "yaml", "yml", "sql"}
DEFAULT_USER_ID = 1


def _file_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")
    return ext


async def _create_document(file: UploadFile, replace_document_id: int | None = None):
    filename = file.filename or "untitled"
    ext = _file_type(filename)
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    db = SessionLocal()
    try:
        replace = db.get(SourceDocument, replace_document_id) if replace_document_id else None
        if replace_document_id and (replace is None or replace.user_id != DEFAULT_USER_ID):
            raise HTTPException(status_code=404, detail="要替换的资料不存在")
        duplicate = db.execute(select(SourceDocument).where(
            SourceDocument.user_id == DEFAULT_USER_ID,
            SourceDocument.content_hash == content_hash,
            SourceDocument.is_active.is_(True),
            SourceDocument.cancel_requested.is_(False),
        )).scalars().first()
        if duplicate:
            return {"duplicate": True, "document": document_payload(duplicate)}

        logical_key = replace.logical_key if replace else str(uuid.uuid4())
        version = (replace.version + 1) if replace else 1
        save_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.{ext}")
        with open(save_path, "wb") as saved:
            saved.write(content)
        doc = SourceDocument(
            user_id=DEFAULT_USER_ID,
            filename=filename,
            file_type=ext,
            storage_path=save_path,
            parse_status="pending",
            content_hash=content_hash,
            logical_key=logical_key,
            version=version,
            is_active=False if replace else True,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
    finally:
        db.close()

    enqueue_parse(doc.id, save_path, filename, ext)
    return {"duplicate": False, "document": document_payload(doc)}


@router.post("")
async def upload_document(file: UploadFile = File(...)):
    return await _create_document(file)


@router.post("/{document_id}/replace")
async def replace_document(document_id: int, file: UploadFile = File(...)):
    return await _create_document(file, replace_document_id=document_id)


@router.get("")
def list_documents():
    db = SessionLocal()
    try:
        docs = db.execute(select(SourceDocument).where(SourceDocument.cancel_requested.is_(False)).order_by(SourceDocument.logical_key, SourceDocument.version.desc())).scalars().all()
        return [document_payload(doc) for doc in docs]
    finally:
        db.close()


@router.get("/{document_id}")
def get_document(document_id: int):
    db = SessionLocal()
    try:
        doc = db.get(SourceDocument, document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="资料不存在")
        return document_payload(doc)
    finally:
        db.close()


@router.delete("/{document_id}")
def delete_document(document_id: int):
    db = SessionLocal()
    try:
        doc = db.get(SourceDocument, document_id)
        if doc is None or doc.user_id != DEFAULT_USER_ID:
            raise HTTPException(status_code=404, detail="资料不存在")
        doc.cancel_requested = True
        doc.is_active = False
        doc.parse_status = "cancelled" if doc.parse_status in {"pending", "parsing"} else "deleted"
        bump_generation(db, doc.user_id)
        db.commit()
        return {"id": doc.id, "status": doc.parse_status}
    finally:
        db.close()
