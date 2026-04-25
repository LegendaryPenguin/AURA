from __future__ import annotations

import copy

import pytest

from server.core.validation import validate_overlay_response


def _base_overlay(**overrides: object) -> dict:
    overlay = {
        "bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
        "label": "motor",
        "confidence": 0.85,
        "ui_layer": "foreground",
        "overlay_type": "diagnostic",
        "action_required": False,
    }
    overlay.update(overrides)
    return overlay


def _base_response(**overrides: object) -> dict:
    resp = {
        "request_id": "req-001",
        "session_id": "sess-001",
        "created_at": "2026-04-25T12:00:00Z",
        "overlays": [_base_overlay()],
    }
    resp.update(overrides)
    return resp


# ── 5 valid fixtures ────────────────────────────────────────────────

class TestValidPayloads:
    def test_minimal_valid(self):
        result = validate_overlay_response(_base_response())
        assert result is not None
        assert len(result["overlays"]) == 1

    def test_all_optional_fields(self):
        payload = _base_response(
            model_version="qwen-vl-7b",
            tracking_state="tracking",
            warnings=["low light"],
        )
        payload["overlays"] = [_base_overlay(
            mask_rle="abc123",
            depth_value=0.42,
            object_id="obj-7",
        )]
        result = validate_overlay_response(payload)
        assert result is not None
        assert result["model_version"] == "qwen-vl-7b"

    def test_multiple_overlays(self):
        payload = _base_response()
        payload["overlays"] = [
            _base_overlay(label="part-a", ui_layer="background"),
            _base_overlay(label="part-b", overlay_type="hazard"),
        ]
        result = validate_overlay_response(payload)
        assert result is not None
        assert len(result["overlays"]) == 2

    def test_boundary_coordinates(self):
        payload = _base_response()
        payload["overlays"] = [_base_overlay(
            bbox={"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
        )]
        result = validate_overlay_response(payload)
        assert result is not None

    def test_confidence_at_floor(self):
        payload = _base_response()
        payload["overlays"] = [_base_overlay(confidence=0.5)]
        result = validate_overlay_response(payload, confidence_floor=0.5)
        assert result is not None


# ── 5 invalid fixtures ─────────────────────────────────────────────

class TestInvalidPayloads:
    def test_coordinates_out_of_bounds(self):
        payload = _base_response()
        payload["overlays"] = [_base_overlay(
            bbox={"x": 1.5, "y": 0.1, "width": 0.2, "height": 0.3},
        )]
        result = validate_overlay_response(payload)
        assert result is None

    def test_missing_required_field(self):
        payload = _base_response()
        del payload["request_id"]
        result = validate_overlay_response(payload)
        assert result is None

    def test_invalid_overlay_type_enum(self):
        payload = _base_response()
        payload["overlays"] = [_base_overlay(overlay_type="unknown")]
        result = validate_overlay_response(payload)
        assert result is None

    def test_invalid_ui_layer_enum(self):
        payload = _base_response()
        payload["overlays"] = [_base_overlay(ui_layer="sky")]
        result = validate_overlay_response(payload)
        assert result is None

    def test_confidence_below_floor(self):
        payload = _base_response()
        payload["overlays"] = [_base_overlay(confidence=0.3)]
        result = validate_overlay_response(payload, confidence_floor=0.5)
        assert result is None


# ── Additional rejection‐returns‐None guarantee ────────────────────

class TestRejectionBehavior:
    def test_none_payload_returns_none(self):
        assert validate_overlay_response(None) is None

    def test_list_payload_returns_none(self):
        assert validate_overlay_response([1, 2, 3]) is None

    def test_rejected_never_raises(self):
        bad_inputs = [None, 42, "", [], {"overlays": "not-a-list"}]
        for bad in bad_inputs:
            result = validate_overlay_response(bad)
            assert result is None
