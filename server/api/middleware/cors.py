from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.utils.config_loader import ConfigError, load_and_validate

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SERVER_CONFIG_PATH = _REPO_ROOT / "config" / "server.yaml"

_DEFAULT_CORS_CONFIG: dict[str, Any] = {
    "allowed_origins": [],
    "allowed_methods": ["GET", "POST", "OPTIONS"],
    "allowed_headers": ["Content-Type", "Authorization"],
    "allow_credentials": False,
}


def _load_cors_config() -> dict[str, Any]:
    """Load CORS config from server.yaml, falling back to safe defaults."""
    try:
        config = load_and_validate(_SERVER_CONFIG_PATH)
        cors_cfg = config.get("cors", {})
        if not isinstance(cors_cfg, dict):
            return dict(_DEFAULT_CORS_CONFIG)
        return {
            "allowed_origins": list(cors_cfg.get("allowed_origins", _DEFAULT_CORS_CONFIG["allowed_origins"])),
            "allowed_methods": list(cors_cfg.get("allowed_methods", _DEFAULT_CORS_CONFIG["allowed_methods"])),
            "allowed_headers": list(cors_cfg.get("allowed_headers", _DEFAULT_CORS_CONFIG["allowed_headers"])),
            "allow_credentials": bool(cors_cfg.get("allow_credentials", _DEFAULT_CORS_CONFIG["allow_credentials"])),
        }
    except (ConfigError, OSError, TypeError, ValueError):
        return dict(_DEFAULT_CORS_CONFIG)


def register_cors_middleware(app: FastAPI) -> None:
    cors_config = _load_cors_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config["allowed_origins"],
        allow_methods=cors_config["allowed_methods"],
        allow_headers=cors_config["allowed_headers"],
        allow_credentials=cors_config["allow_credentials"],
    )
