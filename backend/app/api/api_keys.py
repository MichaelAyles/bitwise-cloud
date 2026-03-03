import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.api_key import ApiKey, ApiKeyDocument
from app.models.document import Document
from app.models.user import User
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyDocumentsUpdate,
    ApiKeyResponse,
    ApiKeyUpdate,
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _make_response(
    api_key: ApiKey, doc_ids: list[uuid.UUID], full_key: str | None = None
) -> dict:
    data = {
        "id": api_key.id,
        "key_prefix": api_key.key_prefix,
        "key_value": api_key.key_value,
        "name": api_key.name,
        "is_active": api_key.is_active,
        "last_used_at": api_key.last_used_at,
        "request_count": api_key.request_count,
        "created_at": api_key.created_at,
        "expires_at": api_key.expires_at,
        "document_ids": doc_ids,
    }
    if full_key is not None:
        data["key"] = full_key
    return data


@router.post(
    "", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    body: ApiKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate document IDs belong to user and are ready
    if body.document_ids:
        result = await db.execute(
            select(Document.id).where(
                Document.id.in_(body.document_ids),
                Document.user_id == user.id,
                Document.status == "ready",
            )
        )
        valid_ids = {row[0] for row in result.fetchall()}
        invalid = set(body.document_ids) - valid_ids
        if invalid:
            raise HTTPException(
                status_code=400, detail=f"Invalid or not-ready document IDs: {invalid}"
            )

    # Generate key: bw_<32 random hex chars>
    raw_key = f"bw_{secrets.token_hex(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:11]  # "bw_" + first 8 hex chars

    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        key_value=raw_key,
        name=body.name,
        expires_at=body.expires_at,
    )
    db.add(api_key)
    await db.flush()

    # Link documents
    for doc_id in body.document_ids:
        db.add(ApiKeyDocument(api_key_id=api_key.id, document_id=doc_id))

    await db.commit()
    await db.refresh(api_key)

    return _make_response(api_key, body.document_ids, full_key=raw_key)


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user.id)
        .order_by(ApiKey.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    keys = result.scalars().all()

    if not keys:
        return []

    # Batch-load all document links for the user's keys in a single query
    api_key_ids = [key.id for key in keys]
    doc_links_result = await db.execute(
        select(ApiKeyDocument.api_key_id, ApiKeyDocument.document_id).where(
            ApiKeyDocument.api_key_id.in_(api_key_ids)
        )
    )
    doc_links_by_key: dict[uuid.UUID, list[uuid.UUID]] = {}
    for row in doc_links_result.fetchall():
        doc_links_by_key.setdefault(row[0], []).append(row[1])

    responses = []
    for key in keys:
        doc_ids = doc_links_by_key.get(key.id, [])
        responses.append(_make_response(key, doc_ids))

    return responses


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    doc_links = await db.execute(
        select(ApiKeyDocument.document_id).where(
            ApiKeyDocument.api_key_id == api_key.id
        )
    )
    doc_ids = [row[0] for row in doc_links.fetchall()]
    return _make_response(api_key, doc_ids)


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: uuid.UUID,
    body: ApiKeyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if body.name is not None:
        api_key.name = body.name
    if body.expires_at is not None:
        api_key.expires_at = body.expires_at

    await db.commit()
    await db.refresh(api_key)

    doc_links = await db.execute(
        select(ApiKeyDocument.document_id).where(
            ApiKeyDocument.api_key_id == api_key.id
        )
    )
    doc_ids = [row[0] for row in doc_links.fetchall()]
    return _make_response(api_key, doc_ids)


@router.put("/{key_id}/documents", response_model=ApiKeyResponse)
async def update_api_key_documents(
    key_id: uuid.UUID,
    body: ApiKeyDocumentsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Validate document IDs
    if body.document_ids:
        valid_result = await db.execute(
            select(Document.id).where(
                Document.id.in_(body.document_ids),
                Document.user_id == user.id,
                Document.status == "ready",
            )
        )
        valid_ids = {row[0] for row in valid_result.fetchall()}
        invalid = set(body.document_ids) - valid_ids
        if invalid:
            raise HTTPException(
                status_code=400, detail=f"Invalid or not-ready document IDs: {invalid}"
            )

    # Replace all document links
    await db.execute(
        ApiKeyDocument.__table__.delete().where(ApiKeyDocument.api_key_id == api_key.id)
    )
    for doc_id in body.document_ids:
        db.add(ApiKeyDocument(api_key_id=api_key.id, document_id=doc_id))

    await db.commit()
    await db.refresh(api_key)

    return _make_response(api_key, body.document_ids)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    await db.commit()
