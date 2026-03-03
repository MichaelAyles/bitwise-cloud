import hashlib
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ApiKeyAuth, get_api_key_auth
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.schemas.document import DocumentResponse, IngestionProgressResponse

router = APIRouter(prefix="/v1/documents", tags=["api"])

PDF_MAGIC = b"%PDF"
MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.get("", response_model=list[DocumentResponse])
@limiter.limit("60/minute")
async def api_list_documents(
    request: Request,
    auth: ApiKeyAuth = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    query = select(Document).where(Document.user_id == auth.user.id)

    if auth.allowed_doc_ids:
        query = query.where(Document.id.in_(auth.allowed_doc_ids))

    query = query.order_by(Document.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/hour")
async def api_upload_document(
    request: Request,
    file: UploadFile,
    title: str | None = Query(None),
    auth: ApiKeyAuth = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
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

    file_hash = hashlib.sha256(content).hexdigest()

    existing = await db.execute(
        select(Document).where(
            Document.user_id == auth.user.id, Document.file_hash == file_hash
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="This document has already been uploaded"
        )

    doc_id = uuid.uuid4()
    upload_dir = Path(settings.upload_dir) / str(auth.user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = upload_dir / f"{doc_id}.pdf"
    pdf_path.write_bytes(content)

    doc = Document(
        id=doc_id,
        user_id=auth.user.id,
        title=title or file.filename or "Untitled",
        filename=file.filename or "document.pdf",
        file_hash=file_hash,
        file_size_bytes=len(content),
        status="pending",
    )
    db.add(doc)

    auth.user.storage_used_bytes += len(content)
    await db.commit()
    await db.refresh(doc)

    from app.worker.tasks import ingest_document

    job = IngestionJob(document_id=doc.id, status="queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = ingest_document.delay(str(doc.id))
    job.celery_task_id = task.id
    await db.commit()

    return doc


@router.get("/{doc_id}/progress", response_model=IngestionProgressResponse)
@limiter.limit("60/minute")
async def api_get_ingestion_progress(
    request: Request,
    doc_id: uuid.UUID,
    auth: ApiKeyAuth = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
) -> IngestionProgressResponse:
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == auth.user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

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
