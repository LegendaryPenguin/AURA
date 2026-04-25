from __future__ import annotations

from fastapi import APIRouter

from server.api.routes.analyze import router as analyze_router
from server.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(analyze_router)

__all__ = ["api_router"]
