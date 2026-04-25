from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_error_handler_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def unhandled_exception_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - framework-level safety net
            status_code = int(getattr(exc, "status_code", 500))
            if status_code < 400:
                status_code = 500

            logger.exception("Unhandled server exception")
            return JSONResponse(
                status_code=status_code,
                content={"error": str(exc), "code": status_code, "stage": "request"},
            )
