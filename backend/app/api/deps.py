import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.api_key import ApiKey, ApiKeyDocument
from app.models.user import User
from app.services.auth_service import decode_token

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_token(credentials.credentials, expected_type="access")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


class ApiKeyAuth:
    """Result of API key authentication — carries user + allowed doc IDs."""

    def __init__(self, user: User, api_key: ApiKey, allowed_doc_ids: list[uuid.UUID]):
        self.user = user
        self.api_key = api_key
        self.allowed_doc_ids = allowed_doc_ids


async def get_api_key_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiKeyAuth:
    """Authenticate via X-API-Key header."""
    raw_key = request.headers.get("X-API-Key")
    if not raw_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key header")

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True))
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    # Load user
    user_result = await db.execute(select(User).where(User.id == api_key.user_id, User.is_active == True))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Load allowed document IDs
    doc_links = await db.execute(
        select(ApiKeyDocument.document_id).where(ApiKeyDocument.api_key_id == api_key.id)
    )
    allowed_doc_ids = [row[0] for row in doc_links.fetchall()]

    # Update usage stats
    api_key.last_used_at = datetime.now(timezone.utc)
    api_key.request_count += 1
    await db.commit()

    return ApiKeyAuth(user=user, api_key=api_key, allowed_doc_ids=allowed_doc_ids)
