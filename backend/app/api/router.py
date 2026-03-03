from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.api_keys import router as api_keys_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.search import api_router as api_v1_router
from app.api.search import router as search_router
from app.api.users import router as users_router
from app.api.v1_documents import router as v1_documents_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(documents_router)
api_router.include_router(api_keys_router)
api_router.include_router(search_router)
api_router.include_router(health_router)
api_router.include_router(admin_router)
api_router.include_router(api_v1_router)
api_router.include_router(v1_documents_router)
