from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage

_VALID_UI_LAYERS = {"background", "midground", "foreground", "hud"}
_VALID_OVERLAY_TYPES = {"diagnostic", "hazard", "info", "reference"}
_OVERLAY_REQUIRED_KEYS = {"bbox", "label", "confidence", "ui_layer", "overlay_type", "action_required"}
_BBOX_REQUIRED_KEYS = {"x", "y", "width", "height"}


def _validate_bbox(bbox: Any) -> None:
    if not isinstance(bbox, dict):
        raise ValueError("Postprocess: overlay bbox must be a dict")
    missing = _BBOX_REQUIRED_KEYS - bbox.keys()
    if missing:
        raise ValueError(f"Postprocess: bbox missing keys: {sorted(missing)}")
    for key in ("x", "y", "width", "height"):
        val = bbox[key]
        if not isinstance(val, (int, float)):
            raise ValueError(f"Postprocess: bbox.{key} must be a number, got {type(val).__name__}")
        if key in ("x", "y") and not (0 <= val <= 1):
            raise ValueError(f"Postprocess: bbox.{key} must be in [0, 1], got {val}")
        if key in ("width", "height") and not (0 < val <= 1):
            raise ValueError(f"Postprocess: bbox.{key} must be in (0, 1], got {val}")


def _validate_overlay(overlay: Any) -> None:
    if not isinstance(overlay, dict):
        raise ValueError("Postprocess: each overlay must be a dict")
    missing = _OVERLAY_REQUIRED_KEYS - overlay.keys()
    if missing:
        raise ValueError(f"Postprocess: overlay missing keys: {sorted(missing)}")

    _validate_bbox(overlay["bbox"])

    if not isinstance(overlay["label"], str) or not overlay["label"]:
        raise ValueError("Postprocess: overlay.label must be a non-empty string")
    conf = overlay["confidence"]
    if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
        raise ValueError(f"Postprocess: overlay.confidence must be in [0, 1], got {conf}")
    if overlay["ui_layer"] not in _VALID_UI_LAYERS:
        raise ValueError(f"Postprocess: invalid ui_layer '{overlay['ui_layer']}'")
    if overlay["overlay_type"] not in _VALID_OVERLAY_TYPES:
        raise ValueError(f"Postprocess: invalid overlay_type '{overlay['overlay_type']}'")
    if not isinstance(overlay["action_required"], bool):
        raise ValueError("Postprocess: overlay.action_required must be a boolean")


class PostprocessStage(PipelineStage):
    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    def execute(self, context: PipelineContext) -> PipelineContext:
        response = context.response or {}
        vlm_result: dict[str, Any] | None = response.get("vlm_result")

        if vlm_result is None:
            raise ValueError("Postprocess: no vlm_result in pipeline context")

        overlays = vlm_result.get("overlays", [])
        if not isinstance(overlays, list):
            raise ValueError("Postprocess: vlm_result.overlays must be a list")

        for i, overlay in enumerate(overlays):
            try:
                _validate_overlay(overlay)
            except ValueError as exc:
                raise ValueError(f"Postprocess: overlay[{i}] invalid — {exc}") from exc

        request_id = response.get("request_id", "")
        session_id = response.get("session_id", "")

        payload: dict[str, Any] = {
            "request_id": request_id,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "overlays": overlays,
        }

        model_version = vlm_result.get("model_version")
        if model_version:
            payload["model_version"] = model_version

        warnings = vlm_result.get("warnings")
        if warnings and isinstance(warnings, list):
            payload["warnings"] = warnings

        context.response = payload
        return context
