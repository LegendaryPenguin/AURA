from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from server.utils.config_loader import ConfigError, load_and_validate

router = APIRouter()

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SERVER_CONFIG_PATH = _REPO_ROOT / "config" / "server.yaml"
_DEFAULT_REQUIRED = ["vlm"]
_DEFAULT_OPTIONAL = ["audio", "sam2", "depth", "generation", "agents"]


def _canonical_backend_name(name: str) -> str:
    return "sam2" if name == "segmentation" else name


def _load_health_config() -> tuple[list[str], list[str]]:
    try:
        config = load_and_validate(_SERVER_CONFIG_PATH)
        health_cfg = config.get("health", {})
        if not isinstance(health_cfg, dict):
            return (_DEFAULT_REQUIRED, _DEFAULT_OPTIONAL)

        required = [_canonical_backend_name(str(name)) for name in health_cfg.get("required_backends", _DEFAULT_REQUIRED)]
        optional = [_canonical_backend_name(str(name)) for name in health_cfg.get("optional_backends", _DEFAULT_OPTIONAL)]
        return (required, optional)
    except (ConfigError, OSError, TypeError, ValueError):
        return (_DEFAULT_REQUIRED, _DEFAULT_OPTIONAL)


def _normalize_status(raw_status: Any) -> str:
    if isinstance(raw_status, str) and raw_status in {"ready", "loading", "error"}:
        return raw_status
    if isinstance(raw_status, bool):
        return "ready" if raw_status else "error"
    return "loading"


def _status_for_backend(runtime_statuses: dict[str, Any], backend: str) -> Any:
    if backend == "sam2":
        if "sam2" in runtime_statuses:
            return runtime_statuses["sam2"]
        return runtime_statuses.get("segmentation")
    return runtime_statuses.get(backend)


@router.get("/health")
async def get_health(request: Request) -> dict[str, Any]:
    required_backends, optional_backends = _load_health_config()
    configured_backends = required_backends + [name for name in optional_backends if name not in required_backends]

    runtime_statuses = getattr(request.app.state, "backend_statuses", {})
    if not isinstance(runtime_statuses, dict):
        runtime_statuses = {}

    models: dict[str, str] = {}
    for backend in configured_backends:
        raw_status = _status_for_backend(runtime_statuses, backend)
        models[backend] = _normalize_status(raw_status)

    all_required_ready = all(models.get(backend) == "ready" for backend in required_backends)
    status = "healthy" if all_required_ready else "degraded"

    return {"status": status, "models": models}
