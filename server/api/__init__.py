from __future__ import annotations

from fastapi import FastAPI

from server.api.middleware import register_cors_middleware, register_error_handler_middleware


def register_api_middleware(app: FastAPI) -> None:
    register_error_handler_middleware(app)
    register_cors_middleware(app)
