from __future__ import annotations

import asyncio
import functools
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import HTTPException

from server.utils.config_loader import ConfigError, load_and_validate

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SERVER_CONFIG_PATH = _REPO_ROOT / "config" / "server.yaml"

_state_lock = asyncio.Lock()
_analyze_in_progress = False


@functools.lru_cache(maxsize=1)
def _load_rate_limit_config() -> dict[str, Any]:
    try:
        config = load_and_validate(_SERVER_CONFIG_PATH)
        rate_limit_cfg = config.get("rate_limit", {})
        if not isinstance(rate_limit_cfg, dict):
            return {"enable_analyze_lock": True}
        return {
            "enable_analyze_lock": bool(rate_limit_cfg.get("enable_analyze_lock", True)),
        }
    except (ConfigError, OSError, TypeError, ValueError):
        return {"enable_analyze_lock": True}


@asynccontextmanager
async def acquire_analyze_slot() -> AsyncIterator[None]:
    """
    Reject concurrent /analyze requests immediately.

    The state lock guards access to a simple in-progress flag so no caller
    blocks behind another request; the second caller gets a 429.
    """
    cfg = _load_rate_limit_config()
    if not cfg["enable_analyze_lock"]:
        yield
        return

    global _analyze_in_progress

    async with _state_lock:
        if _analyze_in_progress:
            raise HTTPException(
                status_code=429,
                detail={"error": "Analyze request already in progress", "code": 429, "stage": "rate_limit"},
            )
        _analyze_in_progress = True

    try:
        yield
    finally:
        async with _state_lock:
            _analyze_in_progress = False
