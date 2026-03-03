import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    expires_at: datetime | None = None
    document_ids: list[uuid.UUID] = []


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    key_prefix: str
    key_value: str | None = None
    name: str
    is_active: bool
    last_used_at: datetime | None
    request_count: int
    created_at: datetime
    expires_at: datetime | None
    document_ids: list[uuid.UUID] = []

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str  # full key, shown only once


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    expires_at: datetime | None = None


class ApiKeyDocumentsUpdate(BaseModel):
    document_ids: list[uuid.UUID]
