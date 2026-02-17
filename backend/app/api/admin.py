import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_admin_user
from app.models.api_key import ApiKey
from app.models.document import Document
from app.models.invite import Invite
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.schemas.admin import (
    AdminDocumentResponse,
    AdminUserResponse,
    AdminUserUpdate,
    InviteCreate,
    InviteResponse,
    SettingUpdate,
    SettingsResponse,
    StatsResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Stats ---

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
    total_docs = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    total_storage = (await db.execute(select(func.coalesce(func.sum(User.storage_used_bytes), 0)))).scalar() or 0

    status_rows = (await db.execute(
        select(Document.status, func.count(Document.id)).group_by(Document.status)
    )).all()
    documents_by_status = {row[0]: row[1] for row in status_rows}

    return StatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_documents=total_docs,
        total_storage_bytes=total_storage,
        documents_by_status=documents_by_status,
    )


# --- Users ---

@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    doc_count_sub = (
        select(Document.user_id, func.count(Document.id).label("doc_count"))
        .group_by(Document.user_id)
        .subquery()
    )
    key_count_sub = (
        select(ApiKey.user_id, func.count(ApiKey.id).label("key_count"))
        .group_by(ApiKey.user_id)
        .subquery()
    )

    result = await db.execute(
        select(
            User,
            func.coalesce(doc_count_sub.c.doc_count, 0).label("document_count"),
            func.coalesce(key_count_sub.c.key_count, 0).label("api_key_count"),
        )
        .outerjoin(doc_count_sub, User.id == doc_count_sub.c.user_id)
        .outerjoin(key_count_sub, User.id == key_count_sub.c.user_id)
        .order_by(User.created_at.desc())
    )

    rows = result.all()
    return [
        AdminUserResponse(
            id=row.User.id,
            email=row.User.email,
            display_name=row.User.display_name,
            is_active=row.User.is_active,
            is_admin=row.User.is_admin,
            created_at=row.User.created_at,
            storage_used_bytes=row.User.storage_used_bytes,
            storage_limit_bytes=row.User.storage_limit_bytes,
            document_count=row.document_count,
            api_key_count=row.api_key_count,
        )
        for row in rows
    ]


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: uuid.UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    doc_count = (await db.execute(select(func.count(Document.id)).where(Document.user_id == user_id))).scalar() or 0
    key_count = (await db.execute(select(func.count(ApiKey.id)).where(ApiKey.user_id == user_id))).scalar() or 0

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        storage_used_bytes=user.storage_used_bytes,
        storage_limit_bytes=user.storage_limit_bytes,
        document_count=doc_count,
        api_key_count=key_count,
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.storage_limit_bytes is not None:
        user.storage_limit_bytes = body.storage_limit_bytes

    await db.commit()
    await db.refresh(user)

    doc_count = (await db.execute(select(func.count(Document.id)).where(Document.user_id == user_id))).scalar() or 0
    key_count = (await db.execute(select(func.count(ApiKey.id)).where(ApiKey.user_id == user_id))).scalar() or 0

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        storage_used_bytes=user.storage_used_bytes,
        storage_limit_bytes=user.storage_limit_bytes,
        document_count=doc_count,
        api_key_count=key_count,
    )


# --- Documents ---

@router.get("/documents", response_model=list[AdminDocumentResponse])
async def list_documents(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document, User.email)
        .join(User, Document.user_id == User.id)
        .order_by(Document.created_at.desc())
    )
    rows = result.all()
    return [
        AdminDocumentResponse(
            id=doc.id,
            title=doc.title,
            filename=doc.filename,
            file_size_bytes=doc.file_size_bytes,
            page_count=doc.page_count,
            status=doc.status,
            chunk_count=doc.chunk_count,
            register_count=doc.register_count,
            created_at=doc.created_at,
            owner_email=email,
            owner_id=doc.user_id,
        )
        for doc, email in rows
    ]


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: uuid.UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await db.delete(doc)
    await db.commit()


# --- Invites ---

@router.get("/invites", response_model=list[InviteResponse])
async def list_invites(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Invite).order_by(Invite.created_at.desc()))
    return result.scalars().all()


@router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteCreate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    # Check for existing pending invite
    existing = await db.execute(select(Invite).where(Invite.email == body.email, Invite.accepted_at == None))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pending invite already exists for this email")

    # Check if user already registered
    existing_user = await db.execute(select(User).where(User.email == body.email))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists")

    invite = Invite(
        email=body.email,
        invited_by=admin.id,
        token=secrets.token_urlsafe(48),
        expires_at=datetime.now(timezone.utc) + timedelta(days=body.expires_in_days),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    return invite


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: uuid.UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Invite).where(Invite.id == invite_id))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")

    if invite.accepted_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot revoke an accepted invite")

    await db.delete(invite)
    await db.commit()


# --- Settings ---

@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "registration_mode"))
    setting = result.scalar_one_or_none()
    return SettingsResponse(registration_mode=setting.value if setting else "invite_only")


@router.patch("/settings", response_model=SettingsResponse)
async def update_settings(
    body: SettingUpdate,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    if body.registration_mode is not None:
        if body.registration_mode not in ("open", "invite_only"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid registration mode. Must be 'open' or 'invite_only'")

        result = await db.execute(select(SystemSetting).where(SystemSetting.key == "registration_mode"))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = body.registration_mode
        else:
            db.add(SystemSetting(key="registration_mode", value=body.registration_mode))

    await db.commit()

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "registration_mode"))
    setting = result.scalar_one_or_none()
    return SettingsResponse(registration_mode=setting.value if setting else "invite_only")
