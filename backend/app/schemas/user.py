import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str | None
    is_admin: bool
    created_at: datetime
    storage_used_bytes: int
    storage_limit_bytes: int

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    display_name: str | None = None
    password: str | None = None
