"""Celery tasks for document ingestion and removal.

Uses synchronous DB access since Celery workers run in a sync context.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.worker.celery_app import celery

logger = logging.getLogger(__name__)

# Sync engine for worker (Celery is sync)
_sync_engine = None


def _get_sync_session() -> Session:
    global _sync_engine
    if _sync_engine is None:
        # Build sync URL from async URL
        db_url = os.environ.get("DATABASE_URL", "")
        sync_url = os.environ.get("SYNC_DATABASE_URL", "")
        if not sync_url:
            sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        _sync_engine = create_engine(sync_url)
    return sessionmaker(bind=_sync_engine)()


@celery.task(bind=True)
def ingest_document(self, document_id: str):
    """Full ingestion pipeline for a single document."""
    from app.models.document import Document

    db = _get_sync_session()
    try:
        doc = db.get(Document, uuid.UUID(document_id))
        if not doc:
            logger.error("Document %s not found", document_id)
            return

        doc.status = "ingesting"
        doc.ingestion_started_at = datetime.now(timezone.utc)
        db.commit()

        pdf_path = Path(os.environ.get("UPLOAD_DIR", "/data/uploads")) / str(doc.user_id) / f"{doc.id}.pdf"
        index_dir = Path(os.environ.get("INDEX_DIR", "/data/indices")) / str(doc.user_id)

        if not pdf_path.exists():
            doc.status = "failed"
            doc.ingestion_error = f"PDF file not found: {pdf_path}"
            db.commit()
            return

        def on_progress(percent: int, message: str):
            self.update_state(state="PROGRESS", meta={"percent": percent, "stage": message})
            logger.info("Ingestion %s: %d%% - %s", document_id, percent, message)

        from app.engine.adapter import IngestionPipeline

        pipeline = IngestionPipeline(
            pdf_path=pdf_path,
            index_dir=index_dir,
            doc_id=str(doc.id),
        )
        result = pipeline.run(progress_callback=on_progress)

        doc.status = "ready"
        doc.page_count = result.page_count
        doc.chunk_count = result.chunk_count
        doc.register_count = result.register_count
        doc.ingestion_completed_at = datetime.now(timezone.utc)
        doc.ingestion_error = None
        db.commit()

        logger.info(
            "Ingestion complete: %s (%d pages, %d chunks, %d registers)",
            document_id,
            result.page_count,
            result.chunk_count,
            result.register_count,
        )

    except Exception as e:
        logger.exception("Ingestion failed for %s", document_id)
        try:
            doc = db.get(Document, uuid.UUID(document_id))
            if doc:
                doc.status = "failed"
                doc.ingestion_error = str(e)[:2000]
                db.commit()
        except Exception:
            logger.exception("Failed to update document status after error")
        raise
    finally:
        db.close()


@celery.task(bind=True)
def remove_document(self, document_id: str):
    """Remove document index files, PDF, and database row."""
    from app.models.document import Document
    from app.models.user import User

    db = _get_sync_session()
    try:
        doc = db.get(Document, uuid.UUID(document_id))
        if not doc:
            logger.warning("Document %s not found for removal", document_id)
            return

        user = db.get(User, doc.user_id)

        # Remove index files
        from app.engine.adapter import remove_document_indices

        index_dir = Path(os.environ.get("INDEX_DIR", "/data/indices")) / str(doc.user_id)
        remove_document_indices(index_dir, str(doc.id))

        # Remove PDF
        pdf_path = Path(os.environ.get("UPLOAD_DIR", "/data/uploads")) / str(doc.user_id) / f"{doc.id}.pdf"
        if pdf_path.exists():
            pdf_path.unlink()

        # Update storage and delete record
        if user:
            user.storage_used_bytes = max(0, user.storage_used_bytes - doc.file_size_bytes)

        db.delete(doc)
        db.commit()

        logger.info("Document %s removed", document_id)

    except Exception:
        logger.exception("Removal failed for %s", document_id)
        raise
    finally:
        db.close()
