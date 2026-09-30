from fastapi import APIRouter
from backend.app.api.auth import router as auth_router
from backend.app.api.cameras import router as cameras_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.settings import router as settings_router
from backend.app.api.system import router as system_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(auth_router)
api_router.include_router(cameras_router)
api_router.include_router(dashboard_router)
api_router.include_router(settings_router)

__all__ = ["api_router"]
