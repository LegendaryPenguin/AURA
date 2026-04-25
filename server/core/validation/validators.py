from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schemas import OverlayResponse, UILayer

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - optional dependency path
    Draft202012Validator = None


_DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "shared" / "schemas" / "overlay_response.json"
_ALLOWED_UI_LAYERS = {layer.value for layer in UILayer}


@lru_cache(maxsize=1)
def _load_json_schema(schema_path: str) -> dict[str, Any]:
    return json.loads(Path(schema_path).read_text(encoding="utf-8"))


def _schema_validate(payload: dict[str, Any], schema_path: Path) -> bool:
    """Return True when the payload satisfies the project JSON schema."""
    if Draft202012Validator is None:
        return True

    schema = _load_json_schema(str(schema_path))
    validator = Draft202012Validator(schema)
    return not any(validator.iter_errors(payload))


def _bbox_in_bounds(overlay: dict[str, Any]) -> bool:
    bbox = overlay.get("bbox")
    if not isinstance(bbox, dict):
        return False

    x = bbox.get("x")
    y = bbox.get("y")
    width = bbox.get("width")
    height = bbox.get("height")

    if not all(isinstance(v, (int, float)) for v in (x, y, width, height)):
        return False
    return 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < width <= 1.0 and 0.0 < height <= 1.0


def _is_valid_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def validate_overlay_response(
    payload: Any,
    *,
    confidence_floor: float = 0.0,
    schema_path: Path | None = None,
) -> dict[str, Any] | None:
    """
    Validate and normalize VLM overlay payloads.

    Returns a validated dictionary or None when the payload is rejected.
    """
    if not 0.0 <= confidence_floor <= 1.0:
        raise ValueError("confidence_floor must be between 0.0 and 1.0")

    if not isinstance(payload, dict):
        return None

    active_schema_path = schema_path or _DEFAULT_SCHEMA_PATH
    if not _schema_validate(payload, active_schema_path):
        return None

    try:
        parsed = OverlayResponse.model_validate(payload)
    except ValidationError:
        return None

    serialized = parsed.model_dump(mode="json")
    overlays = serialized.get("overlays", [])
    if not isinstance(overlays, list):
        return None

    for overlay in overlays:
        if not isinstance(overlay, dict):
            return None
        if not _bbox_in_bounds(overlay):
            return None
        if overlay.get("ui_layer") not in _ALLOWED_UI_LAYERS:
            return None

        confidence = overlay.get("confidence")
        if not isinstance(confidence, (int, float)):
            return None
        if float(confidence) < confidence_floor:
            return None

    if not _is_valid_datetime(serialized.get("created_at")):
        return None

    return serialized
