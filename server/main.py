from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI

from server.api import register_api_middleware
from server.api.routes import api_router
from server.core.pipeline import build_snapshot_pipeline
from server.utils.config_loader import ConfigError, load_and_validate

logger = logging.getLogger(__name__)
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PIPELINE_CONFIG_PATH = _REPO_ROOT / "config" / "pipeline.yaml"


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Keep backend startup optional for early phases.
    Backends are discovered lazily so the API can boot with zero model dependencies.
    """
    app.state.loaded_backends = []
    app.state.backend_statuses = {}
    app.state.snapshot_pipeline = None

    try:
        pipeline_cfg = load_and_validate(_PIPELINE_CONFIG_PATH)
    except (ConfigError, OSError) as exc:
        logger.warning("Pipeline config not loaded; snapshot analysis disabled: %s", exc)
        pipeline_cfg = None

    if pipeline_cfg is not None:
        try:
            import os

            from server.core.inference.vlm.moondream_vl import MoondreamVLBackend
            from server.core.inference.vlm.qwen_vl import QwenVLBackend

            backend_kind = os.getenv("AURA_VLM_BACKEND", "").strip().lower()
            model_id = os.getenv("AURA_VLM_MODEL_ID", "")
            eager_load = True
            if backend_kind == "moondream" or "moondream" in model_id.lower():
                backend = MoondreamVLBackend(model_id=model_id or "vikhyatk/moondream2")
                # Moondream weight load can take minutes; defer to first request.
                eager_load = False
            else:
                backend = QwenVLBackend()
            if eager_load:
                backend.load()
            app.state.loaded_backends = ["vlm"]
            app.state.backend_statuses["vlm"] = "ready" if backend.is_ready() else "loading"
            app.state.snapshot_pipeline = build_snapshot_pipeline(backend, pipeline_cfg)
        except Exception as exc:
            logger.warning("VLM or pipeline startup failed; analyze will use fallback envelope: %s", exc)

    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=app_lifespan)
    register_api_middleware(app)
    app.include_router(api_router)

    @app.on_event("startup")
    async def log_loaded_backends() -> None:
        loaded_backends: Any = getattr(app.state, "loaded_backends", [])
        logger.info("Server startup complete; loaded_backends=%s", loaded_backends)

    return app


app = create_app()
