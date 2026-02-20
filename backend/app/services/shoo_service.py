import time
from dataclasses import dataclass

import httpx
from jose import jwt, JWTError

from app.config import settings

# Cache JWKS for 1 hour
_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0
_JWKS_TTL = 3600


async def _get_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = time.monotonic()
    if _jwks_cache is not None and (now - _jwks_fetched_at) < _JWKS_TTL:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.shoo_jwks_url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = now
        return _jwks_cache


@dataclass
class ShooClaims:
    sub: str
    email: str
    name: str | None
    picture: str | None


class ShooVerificationError(Exception):
    pass


async def verify_shoo_token(id_token: str) -> ShooClaims:
    """Verify a Shoo id_token and return extracted claims."""
    try:
        jwks = await _get_jwks()
    except httpx.HTTPError as e:
        raise ShooVerificationError(f"Failed to fetch Shoo JWKS: {e}") from e

    expected_audience = f"origin:{settings.public_host}"

    try:
        payload = jwt.decode(
            id_token,
            jwks,
            algorithms=["ES256"],
            audience=expected_audience,
            issuer=settings.shoo_issuer,
        )
    except JWTError as e:
        raise ShooVerificationError(f"Invalid Shoo token: {e}") from e

    sub = payload.get("pairwise_sub") or payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise ShooVerificationError("Token missing required claims (sub, email)")

    return ShooClaims(
        sub=sub,
        email=email,
        name=payload.get("name"),
        picture=payload.get("picture"),
    )
