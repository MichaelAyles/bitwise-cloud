from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    checks = {"api": "ok"}

    # Check PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Check Redis
    try:
        import redis as redis_lib

        from app.config import settings

        r = redis_lib.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = "ok"
        r.close()
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    body = {"status": "healthy" if all_ok else "degraded", "checks": checks}
    return JSONResponse(content=body, status_code=200 if all_ok else 503)
