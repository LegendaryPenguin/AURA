"""Phase 1 integration gate: create_app + POST /analyze shape checks."""

from __future__ import annotations

import base64
import io

from fastapi.testclient import TestClient
from PIL import Image

from server.core.pipeline.orchestrator import build_snapshot_pipeline
from server.main import create_app
from shared.interfaces.pipeline_stage import PipelineContext
from tests.fixtures.mocks.mock_inference_backend import MockInferenceBackend


def _valid_jpeg_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(0, 128, 255)).save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class _MockSnapshotPipeline:
    def run(self, context: PipelineContext, session_id: str = "") -> PipelineContext:  # noqa: ARG002
        assert context.response is not None
        assert "image_base64" in context.response
        context.response = {
            "request_id": str(context.response.get("request_id", "r")),
            "session_id": str(context.response.get("session_id", "s")),
            "created_at": "2020-01-01T00:00:00+00:00",
            "model_version": "mock-e2e",
            "overlays": [
                {
                    "bbox": {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2},
                    "label": "phase1-e2e",
                    "confidence": 0.9,
                    "ui_layer": "foreground",
                    "overlay_type": "info",
                    "action_required": False,
                }
            ],
        }
        return context


class _TimeoutSnapshotPipeline:
    def run(self, context: PipelineContext, session_id: str = "") -> PipelineContext:  # noqa: ARG002
        from server.core.pipeline.snapshot_pipeline import PipelineTimeoutError

        raise PipelineTimeoutError("phase1 timeout test")


def test_phase1_post_analyze_end_to_end_schema_shape() -> None:
    app = create_app()
    with TestClient(app) as client:
        app.state.snapshot_pipeline = _MockSnapshotPipeline()
        b64 = _valid_jpeg_b64()
        res = client.post(
            "/analyze",
            json={
                "image_base64": b64,
                "query": "What is this?",
                "request_id": "e2e-req-1",
                "session_id": "e2e-sess-1",
                "capture_ts_ms": 1_700_000_000_000,
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert data["request_id"] == "e2e-req-1"
    assert data["session_id"] == "e2e-sess-1"
    assert "created_at" in data
    assert isinstance(data.get("overlays"), list)
    assert data["overlays"][0]["label"] == "phase1-e2e"


def test_phase1_post_analyze_rejects_missing_required_fields() -> None:
    app = create_app()
    with TestClient(app) as client:
        app.state.snapshot_pipeline = _MockSnapshotPipeline()
        res = client.post(
            "/analyze",
            json={
                "image_base64": _valid_jpeg_b64(),
                "query": "What is this?",
            },
        )
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == 422
    assert "missing required fields" in body["error"]


def test_phase1_post_analyze_rejects_non_object_payload() -> None:
    app = create_app()
    with TestClient(app) as client:
        app.state.snapshot_pipeline = _MockSnapshotPipeline()
        res = client.post("/analyze", json=["not", "an", "object"])
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == 422
    assert "must be an object" in body["error"]


def test_phase1_post_analyze_maps_pipeline_timeout_to_408() -> None:
    app = create_app()
    with TestClient(app) as client:
        app.state.snapshot_pipeline = _TimeoutSnapshotPipeline()
        res = client.post(
            "/analyze",
            json={
                "image_base64": _valid_jpeg_b64(),
                "query": "What is this?",
                "request_id": "e2e-timeout-req",
                "session_id": "e2e-timeout-sess",
                "capture_ts_ms": 1_700_000_000_000,
            },
        )
    assert res.status_code == 408
    body = res.json()
    assert body["code"] == 408
    assert body["stage"] == "pipeline"


def test_phase1_analyze_when_pipeline_unconfigured_returns_fallback_shape() -> None:
    app = create_app()
    with TestClient(app) as client:
        app.state.snapshot_pipeline = None
        b64 = _valid_jpeg_b64()
        res = client.post(
            "/analyze",
            json={
                "image_base64": b64,
                "query": "q",
                "request_id": "e2e-fb",
                "session_id": "e2e-s2",
                "capture_ts_ms": 0,
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert "request_id" in data
    assert "session_id" in data
    assert "created_at" in data
    assert data.get("warnings") == ["snapshot_pipeline_not_configured"]


def test_phase1_post_analyze_with_real_snapshot_pipeline() -> None:
    backend = MockInferenceBackend()
    backend.load()
    config = {
        "orchestrator": {"phase": 1, "include_timing_metadata": False},
        "timeouts": {
            "total_request_timeout_ms": 3000,
            "preprocess_ms": 500,
            "transcribe_ms": 500,
            "analyze_ms": 500,
            "postprocess_ms": 500,
        },
        "preprocess": {
            "expected_image_format": "jpeg",
            "target_width": 640,
            "target_height": 480,
            "keep_aspect_ratio": True,
            "max_image_bytes": 4_194_304,
        },
        "snapshot": {"default_query": "What am I looking at?", "save_debug_artifacts": False},
        "validation": {"confidence_floor": 0.0},
    }

    app = create_app()
    with TestClient(app) as client:
        app.state.snapshot_pipeline = build_snapshot_pipeline(backend, config)
        b64 = _valid_jpeg_b64()
        res = client.post(
            "/analyze",
            json={
                "image_base64": b64,
                "query": "What is this?",
                "request_id": "e2e-real-req-1",
                "session_id": "e2e-real-sess-1",
                "capture_ts_ms": 1_700_000_000_000,
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert data["request_id"] == "e2e-real-req-1"
    assert data["session_id"] == "e2e-real-sess-1"
    assert isinstance(data.get("overlays"), list)
