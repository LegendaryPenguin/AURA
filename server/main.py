from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI

from server.api import register_api_middleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Keep backend startup optional for early phases.
    Backends are discovered lazily so the API can boot with zero model dependencies.
    """
    app.state.loaded_backends = _load_optional_backends()
    yield


def _load_optional_backends() -> list[str]:
    # WS3-A scaffold: no concrete backend loading yet.
    return []


def create_app() -> FastAPI:
    app = FastAPI(lifespan=app_lifespan)
    register_api_middleware(app)

    @app.on_event("startup")
    async def log_loaded_backends() -> None:
        loaded_backends: Any = getattr(app.state, "loaded_backends", [])
        logger.info("Server startup complete; loaded_backends=%s", loaded_backends)

    return app


app = create_app()
