import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class StatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_documents: int
    total_storage_bytes: int
    documents_by_status: dict[str, int]


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime
    storage_used_bytes: int
    storage_limit_bytes: int
    document_count: int
    api_key_count: int

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    storage_limit_bytes: int | None = None


class AdminDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    file_size_bytes: int
    page_count: int | None
    status: str
    chunk_count: int
    register_count: int
    created_at: datetime
    owner_email: str
    owner_id: uuid.UUID

    model_config = {"from_attributes": True}


class InviteCreate(BaseModel):
    email: EmailStr
    expires_in_days: int = 7


class InviteResponse(BaseModel):
    id: uuid.UUID
    email: str
    token: str
    invited_by: uuid.UUID
    accepted_at: datetime | None
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class SettingUpdate(BaseModel):
    registration_mode: str | None = None


class SettingsResponse(BaseModel):
    registration_mode: str
