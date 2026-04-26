from __future__ import annotations

import base64
import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image
import pytest

from server.core.inference.vlm.llava import LlavaVLMBackend
from server.core.inference.vlm.qwen_vl import (
    QwenVLBackend,
    VLM_MIN_DIM,
    VLM_TARGET_DIM,
    _image_bytes_to_data_url,
    _preprocess_image,
)
from tests.contract.test_interface_contracts import _validate_schema_node

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rgb_bytes(width: int, height: int, fmt: str = "PNG") -> bytes:
    """Create a solid-colour test image of *width x height* in *fmt* format."""
    img = Image.new("RGB", (width, height), (120, 80, 200))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP error: {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        self.last_post_payload: dict[str, Any] | None = None

    def get(self, url: str) -> _FakeResponse:
        assert url.endswith("/models")
        return _FakeResponse(
            {
                "data": [
                    {"id": "Qwen/Qwen2.5-VL-3B-Instruct-AWQ"},
                    {"id": "Qwen/Qwen2.5-VL-7B-Instruct"},
                    {"id": "llava-hf/llava-1.5-7b-hf"},
                ]
            }
        )

    def post(self, url: str, json: dict[str, Any]) -> _FakeResponse:
        assert url.endswith("/chat/completions")
        self.last_post_payload = json
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": """```json
{
  "session_id": "session-test",
  "overlays": [
    {
      "bbox": {"x1": -0.5, "y1": 0.2, "x2": 1.5, "y2": 1.3},
      "label": "test-object",
      "confidence": 1.4,
      "ui_layer": "invalid",
      "overlay_type": "invalid",
      "action_required": true
    }
  ],
  "warnings": ["low-light"]
}
```"""
                        }
                    }
                ]
            }
        )


# ---------------------------------------------------------------------------
# Contract / lifecycle tests
# ---------------------------------------------------------------------------

def test_qwen_backend_lifecycle_and_normalized_overlay(monkeypatch: Any) -> None:
    monkeypatch.setattr("server.core.inference.vlm.qwen_vl.httpx.Client", _FakeClient)

    backend = QwenVLBackend(endpoint="http://127.0.0.1:8000/v1")
    backend.load()
    assert backend.is_ready() is True

    backend.warmup()
    assert backend.is_ready() is True

    result = backend.analyze(b"fake-image-bytes", "Locate the object")

    assert {"request_id", "session_id", "created_at", "model_version", "overlays"} <= set(result.keys())
    assert result["session_id"] == "session-test"
    assert isinstance(result["overlays"], list)
    assert len(result["overlays"]) == 1

    overlay = result["overlays"][0]
    bbox = overlay["bbox"]
    assert 0 <= bbox["x"] <= 1
    assert 0 <= bbox["y"] <= 1
    assert 0 < bbox["width"] <= 1
    assert 0 < bbox["height"] <= 1
    assert bbox["x"] + bbox["width"] <= 1
    assert bbox["y"] + bbox["height"] <= 1

    assert 0 <= overlay["confidence"] <= 1
    assert overlay["ui_layer"] == "midground"
    assert overlay["overlay_type"] == "info"
    assert isinstance(overlay["action_required"], bool)
    assert result["warnings"] == ["low-light"]


def test_llava_backend_uses_same_contract(monkeypatch: Any) -> None:
    monkeypatch.setattr("server.core.inference.vlm.qwen_vl.httpx.Client", _FakeClient)

    backend = LlavaVLMBackend(endpoint="http://127.0.0.1:8000/v1")
    backend.load()
    assert backend.is_ready() is True

    result = backend.analyze(b"fake-image-bytes", "Detect visible objects")
    assert "overlays" in result
    assert isinstance(result["overlays"], list)
    assert len(result["overlays"]) == 1


# ---------------------------------------------------------------------------
# Image preprocessing tests
# ---------------------------------------------------------------------------

class TestPreprocessUpscale:
    """Images smaller than VLM_MIN_DIM should be upscaled."""

    def test_tiny_square_upscaled(self) -> None:
        raw = _make_rgb_bytes(4, 4)
        result = _preprocess_image(raw)
        w, h = result.size
        assert min(w, h) >= VLM_MIN_DIM
        assert max(w, h) <= VLM_TARGET_DIM

    def test_tiny_landscape_upscaled_preserves_aspect(self) -> None:
        raw = _make_rgb_bytes(8, 4)
        result = _preprocess_image(raw)
        w, h = result.size
        # Extreme 2:1 ratio — downscale cap wins, so short edge < MIN_DIM is
        # expected.  We verify the long edge is capped and aspect ratio holds.
        assert max(w, h) <= VLM_TARGET_DIM
        ratio_in = 8 / 4
        ratio_out = w / h
        assert abs(ratio_in - ratio_out) < 0.05, f"aspect ratio drift: {ratio_in} -> {ratio_out}"

    def test_tiny_portrait_upscaled_preserves_aspect(self) -> None:
        raw = _make_rgb_bytes(3, 12)
        result = _preprocess_image(raw)
        w, h = result.size
        assert max(w, h) <= VLM_TARGET_DIM
        ratio_in = 3 / 12
        ratio_out = w / h
        assert abs(ratio_in - ratio_out) < 0.05

    def test_tiny_square_meets_min_dim(self) -> None:
        """A square tiny image should satisfy both min and max constraints."""
        raw = _make_rgb_bytes(10, 10)
        result = _preprocess_image(raw)
        w, h = result.size
        assert min(w, h) >= VLM_MIN_DIM
        assert max(w, h) <= VLM_TARGET_DIM

    def test_1x1_warmup_upscaled(self) -> None:
        raw = _make_rgb_bytes(1, 1)
        result = _preprocess_image(raw)
        w, h = result.size
        assert w >= VLM_MIN_DIM
        assert h >= VLM_MIN_DIM
        assert max(w, h) <= VLM_TARGET_DIM


class TestPreprocessDownscale:
    """Images larger than VLM_TARGET_DIM should be downscaled."""

    def test_large_square_downscaled(self) -> None:
        raw = _make_rgb_bytes(1024, 1024)
        result = _preprocess_image(raw)
        w, h = result.size
        assert max(w, h) <= VLM_TARGET_DIM

    def test_large_landscape_downscaled_preserves_aspect(self) -> None:
        raw = _make_rgb_bytes(1920, 1080)
        result = _preprocess_image(raw)
        w, h = result.size
        assert max(w, h) <= VLM_TARGET_DIM
        ratio_in = 1920 / 1080
        ratio_out = w / h
        assert abs(ratio_in - ratio_out) < 0.05

    def test_large_portrait_downscaled_preserves_aspect(self) -> None:
        raw = _make_rgb_bytes(720, 1280)
        result = _preprocess_image(raw)
        w, h = result.size
        assert max(w, h) <= VLM_TARGET_DIM
        ratio_in = 720 / 1280
        ratio_out = w / h
        assert abs(ratio_in - ratio_out) < 0.05


class TestPreprocessPassthrough:
    """Images already within bounds should not be resized."""

    def test_within_bounds_unchanged(self) -> None:
        target = VLM_MIN_DIM + (VLM_TARGET_DIM - VLM_MIN_DIM) // 2
        raw = _make_rgb_bytes(target, target)
        result = _preprocess_image(raw)
        assert result.size == (target, target)


class TestPreprocessEdgeCases:
    """Extreme aspect ratios and the upscale-then-cap path."""

    def test_narrow_strip_capped(self) -> None:
        raw = _make_rgb_bytes(2, 5000)
        result = _preprocess_image(raw)
        w, h = result.size
        assert max(w, h) <= VLM_TARGET_DIM
        assert min(w, h) >= 1

    def test_wide_strip_capped(self) -> None:
        raw = _make_rgb_bytes(5000, 2)
        result = _preprocess_image(raw)
        w, h = result.size
        assert max(w, h) <= VLM_TARGET_DIM
        assert min(w, h) >= 1


class TestDataUrl:
    """_image_bytes_to_data_url produces valid JPEG data URLs."""

    def test_data_url_prefix(self) -> None:
        raw = _make_rgb_bytes(100, 100)
        url = _image_bytes_to_data_url(raw)
        assert url.startswith("data:image/jpeg;base64,")

    def test_data_url_decodes_to_valid_jpeg(self) -> None:
        raw = _make_rgb_bytes(600, 400)
        url = _image_bytes_to_data_url(raw)
        b64_part = url.split(",", 1)[1]
        jpeg_bytes = base64.b64decode(b64_part)
        with Image.open(io.BytesIO(jpeg_bytes)) as img:
            assert img.format == "JPEG"
            assert img.mode == "RGB"
            assert max(img.size) <= VLM_TARGET_DIM

    def test_data_url_from_ppm_format(self) -> None:
        raw = _make_rgb_bytes(300, 300, fmt="PPM")
        url = _image_bytes_to_data_url(raw)
        assert url.startswith("data:image/jpeg;base64,")
        b64_part = url.split(",", 1)[1]
        jpeg_bytes = base64.b64decode(b64_part)
        with Image.open(io.BytesIO(jpeg_bytes)) as img:
            assert img.format == "JPEG"

    def test_data_url_fallback_on_garbage_bytes(self) -> None:
        url = _image_bytes_to_data_url(b"not-an-image")
        assert url.startswith("data:image/jpeg;base64,")


def _bbox_iou(a: dict[str, float], b: dict[str, float]) -> float:
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = a["x"] + a["width"], a["y"] + a["height"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = b["x"] + b["width"], b["y"] + b["height"]

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0.0:
        return 0.0

    area_a = max(0.0, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(0.0, (bx2 - bx1) * (by2 - by1))
    union = area_a + area_b - inter_area
    if union <= 0.0:
        return 0.0
    return inter_area / union


def _load_vlm_ground_truth() -> dict[str, Any]:
    gt_path = PROJECT_ROOT / "tests/fixtures/vlm_ground_truth.json"
    payload = json.loads(gt_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert "cases" in payload
    return payload


def _case_passes(case: dict[str, Any], prediction: dict[str, Any]) -> bool:
    overlays = prediction.get("overlays", [])
    if not isinstance(overlays, list) or not overlays:
        return False

    expected_bbox = case["bbox"]
    min_iou = float(case.get("min_iou", 0.15))
    best_iou = 0.0
    for overlay in overlays:
        if not isinstance(overlay, dict) or "bbox" not in overlay:
            continue
        bbox = overlay["bbox"]
        if not isinstance(bbox, dict):
            continue
        try:
            iou = _bbox_iou(expected_bbox, bbox)
        except KeyError:
            continue
        best_iou = max(best_iou, iou)
    return best_iou >= min_iou


def test_fixture_images_mocked_analyze_outputs_schema_valid(monkeypatch: Any) -> None:
    """All fixture images should survive preprocess + normalize into schema-valid payloads."""
    monkeypatch.setattr("server.core.inference.vlm.qwen_vl.httpx.Client", _FakeClient)

    backend = QwenVLBackend(endpoint="http://127.0.0.1:8000/v1")
    backend.load()
    assert backend.is_ready() is True

    schema_path = PROJECT_ROOT / "shared/schemas/overlay_response.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    fixture_paths = sorted((PROJECT_ROOT / "tests/fixtures/images").glob("*.ppm"))
    assert fixture_paths, "No fixture images found in tests/fixtures/images"

    for fixture_path in fixture_paths:
        raw = fixture_path.read_bytes()
        preprocessed = _preprocess_image(raw)
        assert preprocessed.size[0] > 0 and preprocessed.size[1] > 0

        result = backend.analyze(raw, "Identify objects or obstacles in this image.")
        _validate_schema_node(result, schema, schema, fixture_path.name)

        # Keep explicit date-time verification local to this suite.
        datetime.fromisoformat(result["created_at"])


def test_vlm_ground_truth_dataset_has_20_cases_and_files_exist() -> None:
    payload = _load_vlm_ground_truth()
    cases = payload["cases"]
    assert isinstance(cases, list)
    assert len(cases) == 20

    threshold = float(payload["metrics"]["pass_rate_threshold"])
    assert threshold == 0.8

    for case in cases:
        assert isinstance(case["file"], str) and case["file"]
        assert isinstance(case["label"], str) and case["label"]
        bbox = case["bbox"]
        assert 0.0 <= bbox["x"] <= 1.0
        assert 0.0 <= bbox["y"] <= 1.0
        assert 0.0 < bbox["width"] <= 1.0
        assert 0.0 < bbox["height"] <= 1.0
        assert bbox["x"] + bbox["width"] <= 1.0
        assert bbox["y"] + bbox["height"] <= 1.0
        assert (PROJECT_ROOT / "tests/fixtures/images" / case["file"]).exists()


def test_recorded_accuracy_harness_meets_threshold() -> None:
    """Deterministic CI-safe harness check using recorded-style predictions."""
    payload = _load_vlm_ground_truth()
    cases = payload["cases"]
    threshold = float(payload["metrics"]["pass_rate_threshold"])

    # Simulated recorded predictions: perfect bbox match for every case.
    predictions: dict[str, dict[str, Any]] = {}
    for case in cases:
        predictions[case["file"]] = {
            "overlays": [
                {
                    "bbox": case["bbox"],
                    "label": case["label"],
                    "confidence": 0.9,
                    "ui_layer": "midground",
                    "overlay_type": "info",
                    "action_required": False,
                }
            ]
        }

    passes = 0
    for case in cases:
        if _case_passes(case, predictions[case["file"]]):
            passes += 1
    pass_rate = passes / len(cases)
    assert pass_rate >= threshold


@pytest.mark.vllm
def test_live_vllm_fixture_images_schema_when_enabled() -> None:
    """Optional live check against a running vLLM endpoint (disabled by default)."""
    if os.getenv("AURA_VLM_INTEGRATION") != "1":
        pytest.skip("Set AURA_VLM_INTEGRATION=1 to run live vLLM fixture checks.")

    endpoint = os.getenv("AURA_VLM_ENDPOINT", "http://127.0.0.1:8000/v1")
    model_id = os.getenv("AURA_VLM_MODEL_ID", "Qwen/Qwen2.5-VL-3B-Instruct-AWQ")
    backend = QwenVLBackend(
        endpoint=endpoint,
        model_id=model_id,
        timeout_ms=int(os.getenv("AURA_VLM_TIMEOUT_MS", "30000")),
        max_tokens=int(os.getenv("AURA_VLM_MAX_TOKENS", "160")),
    )
    backend.load()
    if not backend.is_ready():
        pytest.skip(f"vLLM endpoint not ready at {endpoint} for model {model_id}")

    schema_path = PROJECT_ROOT / "shared/schemas/overlay_response.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    fixture_paths = sorted((PROJECT_ROOT / "tests/fixtures/images").glob("*.ppm"))
    assert fixture_paths, "No fixture images found in tests/fixtures/images"

    for fixture_path in fixture_paths:
        result = backend.analyze(
            fixture_path.read_bytes(),
            "Identify objects or obstacles in this image.",
        )
        _validate_schema_node(result, schema, schema, fixture_path.name)
        datetime.fromisoformat(result["created_at"])

        # Keep live assertions stable: overlays can be empty on some model/image pairs.
        for overlay in result.get("overlays", []):
            bbox = overlay["bbox"]
            assert 0.0 <= bbox["x"] <= 1.0
            assert 0.0 <= bbox["y"] <= 1.0
            assert 0.0 < bbox["width"] <= 1.0
            assert 0.0 < bbox["height"] <= 1.0


@pytest.mark.vllm
def test_live_vllm_accuracy_against_ground_truth_when_enabled() -> None:
    """Optional live benchmark gate: pass-rate across 20 labeled fixtures."""
    if os.getenv("AURA_VLM_INTEGRATION") != "1":
        pytest.skip("Set AURA_VLM_INTEGRATION=1 to run live vLLM accuracy benchmark.")

    payload = _load_vlm_ground_truth()
    cases = payload["cases"]
    threshold = float(payload["metrics"]["pass_rate_threshold"])

    endpoint = os.getenv("AURA_VLM_ENDPOINT", "http://127.0.0.1:8000/v1")
    model_id = os.getenv("AURA_VLM_MODEL_ID", "Qwen/Qwen2.5-VL-3B-Instruct-AWQ")
    backend = QwenVLBackend(
        endpoint=endpoint,
        model_id=model_id,
        timeout_ms=int(os.getenv("AURA_VLM_TIMEOUT_MS", "30000")),
        max_tokens=int(os.getenv("AURA_VLM_MAX_TOKENS", "160")),
    )
    backend.load()
    if not backend.is_ready():
        pytest.skip(f"vLLM endpoint not ready at {endpoint} for model {model_id}")

    passes = 0
    for case in cases:
        image_path = PROJECT_ROOT / "tests/fixtures/images" / case["file"]
        try:
            result = backend.analyze(image_path.read_bytes(), "Identify the main object in this image.")
        except Exception:
            # Live-model outputs can occasionally be malformed JSON; count this
            # sample as a miss instead of aborting the full benchmark run.
            continue
        if _case_passes(case, result):
            passes += 1

    pass_rate = passes / len(cases)
    assert pass_rate >= threshold, f"pass_rate={pass_rate:.3f} < threshold={threshold:.3f}"
