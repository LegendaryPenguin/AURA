from __future__ import annotations

import importlib
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
    Load optional VLM + snapshot pipeline. Server boots even if inference is unavailable;
    /analyze then uses the not-configured fallback in routes when `snapshot_pipeline` is None.
    """
    app.state.loaded_backends = []
    app.state.backend_statuses = {}
    app.state.snapshot_pipeline = None

    try:
        pipeline_cfg = load_and_validate(_PIPELINE_CONFIG_PATH)
    except (ConfigError, OSError) as exc:
        logger.warning("Pipeline config not loaded; snapshot analysis disabled: %s", exc)
    else:
        try:
            vlm_mod = importlib.import_module("server.core.inference.vlm.qwen_vl")
            qwen_cls: Any = getattr(vlm_mod, "QwenVLBackend")
            backend = qwen_cls()
        except Exception as exc:
            logger.warning("VLM import/instantiate failed: %s", exc)
        else:
            try:
                backend.load()
            except Exception as exc:
                logger.warning("VLM backend load failed; /analyze will use not-configured fallback: %s", exc)
            else:
                app.state.loaded_backends = ["vlm"]
                app.state.backend_statuses["vlm"] = "ready" if backend.is_ready() else "loading"
                try:
                    app.state.snapshot_pipeline = build_snapshot_pipeline(backend, pipeline_cfg)
                except Exception as exc:
                    logger.warning("Snapshot pipeline build failed: %s", exc)

    has_pipeline = getattr(app.state, "snapshot_pipeline", None) is not None
    logger.info(
        "Server startup: loaded_backends=%s snapshot_pipeline_configured=%s",
        getattr(app.state, "loaded_backends", []),
        has_pipeline,
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=app_lifespan)
    register_api_middleware(app)
    app.include_router(api_router)
    return app


app = create_app()
