"""资料上传与列表。"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models.database import get_db
from app.models.document import Chunk, Document
from app.schemas.document import DocumentListOut, DocumentOut
from app.services import document_service

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _to_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        status=doc.status,
        chunk_count=doc.chunk_count,
        char_count=doc.char_count,
        error_reason=doc.error_reason,
        created_at=doc.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    )


@router.post("", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentOut:
    if not file.filename:
        raise AppError("bad_request", "缺少文件名")
    raw = await file.read()

    # 校验格式 / 大小 / 真实类型（校验失败属于「失败」，按 PRD 记 error_reason）
    try:
        file_type = document_service.validate_upload(file.filename, len(raw), raw[:16])
    except document_service.DocumentParseError as exc:
        doc = Document(
            filename=document_service.safe_filename(file.filename),
            stored_name="",
            file_type=document_service.extension_of(file.filename) or "unknown",
            status="失败",
            chunk_count=0,
            char_count=0,
            error_reason=str(exc),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return _to_out(doc)

    # 落盘
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{file_type}"
    path: Path = settings.uploads_dir / stored_name
    path.write_bytes(raw)

    # 解析 + 切段
    try:
        status, chunks, char_count = document_service.parse_and_chunk(file_type, path)
    except document_service.DocumentParseError as exc:
        doc = Document(
            filename=document_service.safe_filename(file.filename),
            stored_name=stored_name,
            file_type=file_type,
            status="失败",
            chunk_count=0,
            char_count=0,
            error_reason=str(exc),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return _to_out(doc)

    doc = Document(
        filename=document_service.safe_filename(file.filename),
        stored_name=stored_name,
        file_type=file_type,
        status=status,
        chunk_count=len(chunks),
        char_count=char_count,
        error_reason="扫描件，无文字，检索不到" if status == "无文字" else None,
    )
    db.add(doc)
    db.flush()

    for i, text in enumerate(chunks, start=1):
        db.add(Chunk(document_id=doc.id, chunk_index=i, text=text))

    db.commit()
    db.refresh(doc)
    return _to_out(doc)


@router.get("", response_model=DocumentListOut)
def list_documents(db: Session = Depends(get_db)) -> DocumentListOut:
    docs = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return DocumentListOut(items=[_to_out(d) for d in docs])
