import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    DocumentUpdate,
    IngestionProgressResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])

PDF_MAGIC = b"%PDF"
MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post(
    "/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {settings.max_upload_size_mb}MB)",
        )

    if not content[:4].startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=400, detail="File does not appear to be a valid PDF"
        )

    if user.storage_used_bytes + len(content) > user.storage_limit_bytes:
        raise HTTPException(status_code=413, detail="Storage limit exceeded")

    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    existing = await db.execute(
        select(Document).where(
            Document.user_id == user.id, Document.file_hash == file_hash
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="This document has already been uploaded"
        )

    doc_id = uuid.uuid4()
    upload_dir = Path(settings.upload_dir) / str(user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / f"{doc_id}.pdf"
    pdf_path.write_bytes(content)

    doc = Document(
        id=doc_id,
        user_id=user.id,
        title=file.filename or "Untitled",
        filename=file.filename or "document.pdf",
        file_hash=file_hash,
        file_size_bytes=len(content),
        status="pending",
    )
    db.add(doc)

    # Update user storage
    user.storage_used_bytes += len(content)
    await db.commit()
    await db.refresh(doc)

    # Trigger ingestion
    from app.worker.tasks import ingest_document

    job = IngestionJob(document_id=doc.id, status="queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = ingest_document.delay(str(doc.id))
    job.celery_task_id = task.id
    await db.commit()

    return doc


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.patch("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: uuid.UUID,
    body: DocumentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.title = body.title
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = "removing"
    await db.commit()

    from app.worker.tasks import remove_document

    remove_document.delay(str(doc.id))


@router.get("/{doc_id}/progress", response_model=IngestionProgressResponse)
async def get_ingestion_progress(
    doc_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check Celery task state for real-time progress
    job_result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.document_id == doc.id)
        .order_by(IngestionJob.created_at.desc())
    )
    job = job_result.scalar_one_or_none()

    if job and job.celery_task_id:
        from app.worker.celery_app import celery

        task_result = celery.AsyncResult(job.celery_task_id)
        if task_result.state == "PROGRESS":
            meta = task_result.info or {}
            return IngestionProgressResponse(
                status="ingesting",
                progress_percent=meta.get("percent", 0),
                progress_message=meta.get("stage", ""),
            )

    # Fall back to document status
    progress_map = {
        "pending": 0,
        "ingesting": 10,
        "ready": 100,
        "failed": 0,
        "removing": 0,
    }
    return IngestionProgressResponse(
        status=doc.status,
        progress_percent=progress_map.get(doc.status, 0),
        progress_message=doc.ingestion_error if doc.status == "failed" else None,
    )
