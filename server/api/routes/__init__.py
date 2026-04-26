from __future__ import annotations

from fastapi import APIRouter

from server.api.routes.analyze import router as analyze_router
from server.api.routes.agents import router as agents_router
from server.api.routes.health import router as health_router
from server.api.routes.stream import router as stream_router
from server.api.routes.video_sim import router as video_sim_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(analyze_router)
api_router.include_router(video_sim_router)
api_router.include_router(stream_router)
api_router.include_router(agents_router)

__all__ = ["api_router"]
