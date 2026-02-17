import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    file_size_bytes: int
    page_count: int | None
    status: str
    chunk_count: int
    register_count: int
    ingestion_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    title: str


class IngestionProgressResponse(BaseModel):
    status: str
    progress_percent: int
    progress_message: str | None
