"""WS3-B: REST routes — /analyze contract and /health."""

from __future__ import annotations

import base64
import io
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from server.api.middleware import register_cors_middleware, register_error_handler_middleware
from server.api.routes import api_router
from server.api.routes import health
from server.core.pipeline.snapshot_pipeline import PipelineTimeoutError
from shared.interfaces.pipeline_stage import PipelineContext


def _valid_jpeg_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(0, 128, 255)).save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class _OkPipeline:
    def run(self, context: PipelineContext, session_id: str = "") -> PipelineContext:
        assert context.response is not None
        assert "image_base64" in context.response
        context.response = {
            "request_id": str(context.response.get("request_id", "r")),
            "session_id": str(context.response.get("session_id", "s")),
            "created_at": "2020-01-01T00:00:00+00:00",
            "overlays": [
                {
                    "bbox": {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2},
                    "label": "obj",
                    "confidence": 0.9,
                    "ui_layer": "foreground",
                    "overlay_type": "info",
                    "action_required": False,
                }
            ],
        }
        return context


class _TimeoutPipeline:
    def run(self, context: PipelineContext, session_id: str = "") -> PipelineContext:  # noqa: ARG002
        raise PipelineTimeoutError("stalled")


def _app_with_state(snapshot_pipeline: Any) -> FastAPI:
    app = FastAPI()
    register_error_handler_middleware(app)
    register_cors_middleware(app)
    app.include_router(api_router)
    app.state.snapshot_pipeline = snapshot_pipeline
    app.state.backend_statuses = {"vlm": "ready"}
    return app


def test_post_analyze_accepts_image_base64() -> None:
    app = _app_with_state(_OkPipeline())
    b64 = _valid_jpeg_b64()
    with TestClient(app) as client:
        res = client.post(
            "/analyze",
            json={
                "image_base64": b64,
                "query": "What is this?",
                "request_id": "req-1",
                "session_id": "sess-1",
                "capture_ts_ms": 1_700_000_000_000,
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert data["request_id"] == "req-1"
    assert data["session_id"] == "sess-1"
    assert len(data.get("overlays", [])) == 1
    assert data["overlays"][0]["label"] == "obj"


def test_post_analyze_rejects_invalid_image() -> None:
    app = _app_with_state(_OkPipeline())
    with TestClient(app) as client:
        res = client.post(
            "/analyze",
            json={
                "image_base64": "not-valid-b64-!!!",
                "query": "q",
                "capture_ts_ms": 0,
            },
        )
    assert res.status_code == 422


def test_post_analyze_pipeline_timeout_408() -> None:
    app = _app_with_state(_TimeoutPipeline())
    b64 = _valid_jpeg_b64()
    with TestClient(app) as client:
        res = client.post(
            "/analyze",
            json={
                "image_base64": b64,
                "query": "q",
                "capture_ts_ms": 0,
            },
        )
    assert res.status_code == 408
    assert res.json()["code"] == 408


def test_get_health() -> None:
    app = FastAPI()
    app.include_router(health.router)
    app.state.backend_statuses = {"vlm": "ready"}
    with TestClient(app) as client:
        res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in {"healthy", "degraded"}
    assert "vlm" in body["models"]
