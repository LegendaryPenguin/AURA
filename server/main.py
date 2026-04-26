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
_MODELS_CONFIG_PATH = _REPO_ROOT / "config" / "models.yaml"


def _try_load_backend(
    module_path: str, class_name: str, backend_name: str, **kwargs: Any
) -> Any | None:
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        instance = cls(**kwargs)
        instance.load()
        if instance.is_ready():
            logger.info("%s backend loaded and ready", backend_name)
            return instance
        logger.warning("%s backend loaded but not ready", backend_name)
        return instance
    except Exception as exc:
        logger.warning("%s backend unavailable: %s", backend_name, exc)
        return None


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Load inference backends and build the snapshot pipeline.
    Server boots even if some backends are unavailable; /analyze then uses
    the not-configured fallback in routes when snapshot_pipeline is None.
    """
    app.state.loaded_backends = []
    app.state.backend_statuses = {}
    app.state.snapshot_pipeline = None
    app.state.whisper_backend = None
    app.state.sam2_backend = None

    try:
        pipeline_cfg = load_and_validate(_PIPELINE_CONFIG_PATH)
    except (ConfigError, OSError) as exc:
        logger.warning("Pipeline config not loaded; snapshot analysis disabled: %s", exc)
        yield
        return

    models_cfg: dict[str, Any] = {}
    try:
        models_cfg = load_and_validate(_MODELS_CONFIG_PATH)
    except (ConfigError, OSError):
        logger.info("Models config not found; using defaults")

    vlm_backend = _try_load_backend(
        "server.core.inference.vlm.qwen_vl", "QwenVLBackend", "VLM"
    )
    if vlm_backend:
        app.state.loaded_backends.append("vlm")
        app.state.backend_statuses["vlm"] = "ready" if vlm_backend.is_ready() else "loading"

    whisper_backend = _try_load_backend(
        "server.core.inference.audio.whisper_backend",
        "WhisperBackend",
        "Whisper",
        model_size=models_cfg.get("audio", {}).get("provider", "base").replace("whisper-", ""),
    )
    if whisper_backend and whisper_backend.is_ready():
        app.state.whisper_backend = whisper_backend
        app.state.loaded_backends.append("whisper")
        app.state.backend_statuses["whisper"] = "ready"

    seg_cfg = models_cfg.get("segmentation", {})
    sam2_backend = _try_load_backend(
        "server.core.inference.segmentation.sam2_backend",
        "SAM2Backend",
        "SAM2",
        checkpoint_path=str(_REPO_ROOT / seg_cfg.get("checkpoint_path", "models/sam2/sam2_large.pt")),
    )
    if sam2_backend:
        app.state.sam2_backend = sam2_backend
        app.state.loaded_backends.append("sam2")
        app.state.backend_statuses["sam2"] = "ready" if sam2_backend.is_ready() else "fallback"

    if vlm_backend:
        try:
            app.state.snapshot_pipeline = build_snapshot_pipeline(
                vlm_backend, pipeline_cfg,
                segmentation_backend=sam2_backend,
                whisper_backend=whisper_backend,
            )
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
