from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models.invite import Invite
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.schemas.admin import SettingsResponse
from app.schemas.auth import LoginRequest, OAuthRequest, RegisterRequest, TokenResponse
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.shoo_service import ShooVerificationError, verify_shoo_token

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/auth/refresh",
    )


async def _get_registration_mode(db: AsyncSession) -> str:
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "registration_mode")
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else "invite_only"


@router.get("/settings", response_model=SettingsResponse)
async def public_settings(db: AsyncSession = Depends(get_db)):
    mode = await _get_registration_mode(db)
    return SettingsResponse(registration_mode=mode)


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    mode = await _get_registration_mode(db)

    invite = None
    if mode == "invite_only":
        if not body.invite_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is invite-only. An invite token is required.",
            )

        result = await db.execute(
            select(Invite).where(Invite.token == body.invite_token)
        )
        invite = result.scalar_one_or_none()

        if invite is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invite token"
            )

        if invite.accepted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite has already been used",
            )

        if invite.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invite has expired"
            )

        if invite.email.lower() != body.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email does not match invite",
            )

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        invited_by=invite.invited_by if invite else None,
    )
    db.add(user)

    if invite:
        invite.accepted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled"
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token)


@router.post("/oauth/shoo", response_model=TokenResponse)
@limiter.limit("10/minute")
async def oauth_shoo(
    request: Request,
    body: OAuthRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        claims = await verify_shoo_token(body.id_token)
    except ShooVerificationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    # Look up by OAuth identity
    result = await db.execute(
        select(User).where(User.oauth_provider == "shoo", User.oauth_sub == claims.sub)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Only link to existing account if email is verified
        if claims.email_verified:
            result = await db.execute(select(User).where(User.email == claims.email))
            user = result.scalar_one_or_none()
            if user is not None:
                user.oauth_provider = "shoo"
                user.oauth_sub = claims.sub

        if user is None:
            # Auto-register new OAuth user
            user = User(
                email=claims.email,
                display_name=claims.name,
                oauth_provider="shoo",
                oauth_sub=claims.sub,
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled"
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    # Accept refresh token from cookie or Authorization header
    token = None
    if credentials:
        token = credentials.credentials

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token provided"
        )

    user_id = decode_token(token, expected_type="refresh")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, new_refresh_token)

    return TokenResponse(access_token=access_token)
