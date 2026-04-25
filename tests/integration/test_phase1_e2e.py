"""Phase 1 integration gate: real FastAPI app + POST /analyze contract (see MASTER_ROADMAP)."""

from __future__ import annotations

import base64
import io

from fastapi.testclient import TestClient
from PIL import Image

from server.main import create_app
from shared.interfaces.pipeline_stage import PipelineContext


def _valid_jpeg_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(0, 128, 255)).save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class _MockSnapshotPipeline:
    """Minimal pipeline that proves route hands off a context with image_base64."""

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
    assert len(data["overlays"]) >= 1
    o0 = data["overlays"][0]
    assert o0["label"] == "phase1-e2e"
    for key in ("x", "y", "width", "height"):
        assert key in o0["bbox"]


def test_phase1_analyze_when_pipeline_unconfigured_returns_fallback_shape() -> None:
    """Server boots without VLM; /analyze should still return a valid overlay response envelope."""
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
    assert "overlays" in data
    assert data.get("warnings") == ["snapshot_pipeline_not_configured"]
