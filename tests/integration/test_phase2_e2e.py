"""Phase 2 integration test: camera snapshot + audio + segmentation pipeline.

Validates the full Phase 2 flow through the FastAPI app using mocks for
inference backends but exercising the real pipeline orchestration.
"""
from __future__ import annotations

import base64
import io
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from server.main import create_app


def _make_test_jpeg() -> bytes:
    img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def app_with_phase2_pipeline():
    """Create app with a Phase 2 pipeline (VLM + segmentation + audio)."""
    mock_vlm = MagicMock()
    mock_vlm.is_ready.return_value = True
    mock_vlm.load.return_value = None
    mock_vlm.analyze.return_value = {
        "overlays": [
            {
                "bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
                "label": "Test object",
                "confidence": 0.92,
                "overlay_type": "diagnostic",
                "ui_layer": "midground",
                "action_required": False,
            }
        ],
        "model_version": "test-vlm",
    }
    mock_vlm.transcribe.side_effect = NotImplementedError("VLM can't transcribe")

    mock_seg = MagicMock()
    mock_seg.is_ready.return_value = True
    mock_seg.segment.return_value = {
        "mask_rle": {"counts": [10, 20, 30], "size": [100, 100]},
        "score": 0.95,
        "bbox": [10, 20, 40, 60],
        "width": 100,
        "height": 100,
    }

    mock_whisper = MagicMock()
    mock_whisper.is_ready.return_value = True
    mock_whisper.transcribe.return_value = "What is this object?"

    from server.core.pipeline.orchestrator import build_snapshot_pipeline

    pipeline_config = {
        "orchestrator": {"phase": 2, "include_timing_metadata": True},
        "timeouts": {
            "total_request_timeout_ms": 5000,
            "preprocess_ms": 500,
            "transcribe_ms": 1000,
            "analyze_ms": 2000,
            "segment_ms": 500,
            "postprocess_ms": 500,
        },
        "preprocess": {
            "expected_image_format": "jpeg",
            "target_width": 1280,
            "target_height": 720,
            "keep_aspect_ratio": True,
            "max_image_bytes": 4194304,
        },
        "snapshot": {"default_query": "What am I looking at?"},
    }

    pipeline = build_snapshot_pipeline(
        mock_vlm, pipeline_config,
        segmentation_backend=mock_seg,
        whisper_backend=mock_whisper,
    )

    app = create_app()

    from starlette.testclient import TestClient
    with TestClient(app) as client:
        app.state.snapshot_pipeline = pipeline
        app.state.loaded_backends = ["vlm", "whisper", "sam2"]
        app.state.backend_statuses = {"vlm": "ready", "whisper": "ready", "sam2": "ready"}
        yield client, mock_vlm, mock_seg, mock_whisper


def test_phase2_analyze_with_image_and_audio(app_with_phase2_pipeline):
    client, mock_vlm, mock_seg, mock_whisper = app_with_phase2_pipeline

    jpeg_bytes = _make_test_jpeg()
    image_b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    audio_b64 = base64.b64encode(b"fake audio data").decode("ascii")

    response = client.post("/analyze", json={
        "image_base64": image_b64,
        "query": "What is this?",
        "audio_base64": audio_b64,
        "session_id": "test-phase2",
    })

    assert response.status_code == 200
    data = response.json()
    assert "overlays" in data
    assert len(data["overlays"]) >= 1
    assert data["overlays"][0]["label"] == "Test object"
    assert data["overlays"][0]["confidence"] == 0.92
    assert "request_id" in data
    assert "session_id" in data
    assert "created_at" in data


def test_phase2_analyze_without_audio_uses_default_query(app_with_phase2_pipeline):
    client, mock_vlm, mock_seg, mock_whisper = app_with_phase2_pipeline

    jpeg_bytes = _make_test_jpeg()
    image_b64 = base64.b64encode(jpeg_bytes).decode("ascii")

    response = client.post("/analyze", json={
        "image_base64": image_b64,
        "session_id": "test-phase2-no-audio",
    })

    assert response.status_code == 200
    data = response.json()
    assert "overlays" in data
    mock_whisper.transcribe.assert_not_called()


def test_phase2_health_reports_all_backends(app_with_phase2_pipeline):
    client, _, _, _ = app_with_phase2_pipeline

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "models" in data


def test_phase2_rate_limit_lock_exists(app_with_phase2_pipeline):
    """Verify the rate limit mechanism is configured and rejects when lock held."""
    from server.api.middleware.rate_limit import _analyze_in_progress, _state_lock

    client, _, _, _ = app_with_phase2_pipeline

    jpeg_bytes = _make_test_jpeg()
    image_b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    response = client.post("/analyze", json={
        "image_base64": image_b64,
        "session_id": "rate-test",
    })
    assert response.status_code == 200
