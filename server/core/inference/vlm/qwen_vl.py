from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from PIL import Image

from shared.interfaces.inference_base import InferenceBackend

_log = logging.getLogger(__name__)

_ALLOWED_UI_LAYERS = {"background", "midground", "foreground", "hud"}
_ALLOWED_OVERLAY_TYPES = {"diagnostic", "hazard", "info", "reference"}
_ALLOWED_TRACKING_STATES = {"inactive", "initializing", "tracking", "lost"}

_SYSTEM_PROMPT = """You are a vision-language backend for an AR system.
Return ONLY valid JSON. No markdown, no code fences, no prose.

Required output shape:
{
  "overlays": [
    {
      "bbox": {"x": number, "y": number, "width": number, "height": number},
      "label": string,
      "confidence": number,
      "ui_layer": "background" | "midground" | "foreground" | "hud",
      "overlay_type": "diagnostic" | "hazard" | "info" | "reference",
      "action_required": boolean
    }
  ],
  "warnings": [string]
}

Rules:
- bbox values MUST be normalized to [0,1].
- width and height MUST be > 0.
- confidence MUST be in [0,1].
- Return at most 1 overlay unless the user explicitly asks for multiple objects.
- Keep labels concise (1-3 words).
- Keep warnings empty unless there is a real issue.
- Do not include optional fields unless they are necessary.
- If at least one plausible object/region is visible, return one best-effort overlay.
- Use empty overlays only when the image is truly blank/unreadable.
- If unsure, return an empty overlays array and explain in warnings.
"""

_WARMUP_IMAGE_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5Q5RkAAAAASUVORK5CYII="
)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_bbox(bbox_like: Any, overlay: dict[str, Any]) -> dict[str, float]:
    x = y = 0.0
    width = height = 0.001

    if isinstance(bbox_like, dict):
        if {"x", "y", "width", "height"}.issubset(bbox_like):
            x = _to_float(bbox_like.get("x"), 0.0)
            y = _to_float(bbox_like.get("y"), 0.0)
            width = _to_float(bbox_like.get("width"), 0.001)
            height = _to_float(bbox_like.get("height"), 0.001)
        elif {"x1", "y1", "x2", "y2"}.issubset(bbox_like):
            x1 = _to_float(bbox_like.get("x1"), 0.0)
            y1 = _to_float(bbox_like.get("y1"), 0.0)
            x2 = _to_float(bbox_like.get("x2"), x1 + 0.001)
            y2 = _to_float(bbox_like.get("y2"), y1 + 0.001)
            x, y = min(x1, x2), min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
        elif {"left", "top", "right", "bottom"}.issubset(bbox_like):
            left = _to_float(bbox_like.get("left"), 0.0)
            top = _to_float(bbox_like.get("top"), 0.0)
            right = _to_float(bbox_like.get("right"), left + 0.001)
            bottom = _to_float(bbox_like.get("bottom"), top + 0.001)
            x, y = min(left, right), min(top, bottom)
            width = abs(right - left)
            height = abs(bottom - top)
    elif isinstance(bbox_like, list) and len(bbox_like) >= 4:
        x = _to_float(bbox_like[0], 0.0)
        y = _to_float(bbox_like[1], 0.0)
        width = _to_float(bbox_like[2], 0.001)
        height = _to_float(bbox_like[3], 0.001)
    else:
        x = _to_float(overlay.get("x"), 0.0)
        y = _to_float(overlay.get("y"), 0.0)
        width = _to_float(overlay.get("width"), 0.001)
        height = _to_float(overlay.get("height"), 0.001)

    x = _clamp(x, 0.0, 1.0)
    y = _clamp(y, 0.0, 1.0)
    width = _clamp(width, 0.001, 1.0)
    height = _clamp(height, 0.001, 1.0)

    if x + width > 1.0:
        width = max(0.001, 1.0 - x)
    if y + height > 1.0:
        height = max(0.001, 1.0 - y)

    return {"x": x, "y": y, "width": width, "height": height}


def _extract_json_object(raw_content: Any) -> dict[str, Any]:
    if isinstance(raw_content, dict):
        return raw_content
    if isinstance(raw_content, list):
        # Some models return overlays directly as a JSON array.
        if raw_content and isinstance(raw_content[0], dict) and "bbox" in raw_content[0]:
            return {"overlays": raw_content}

    if isinstance(raw_content, list):
        text_parts: list[str] = []
        for part in raw_content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        raw_text = "\n".join(text_parts)
    else:
        raw_text = str(raw_content or "")

    candidate = raw_text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"overlays": parsed}
    except json.JSONDecodeError:
        pass

    # VLMs sometimes emit valid JSON followed by extra text or multiple objects.
    # Use the JSONDecoder to consume only the first valid token.
    decoder = json.JSONDecoder()
    for start_char in ("{", "["):
        idx = candidate.find(start_char)
        if idx == -1:
            continue
        try:
            obj, _ = decoder.raw_decode(candidate, idx)
            if isinstance(obj, dict):
                return obj
            if isinstance(obj, list):
                return {"overlays": obj}
        except json.JSONDecodeError:
            continue

    raise ValueError("Model response did not include a valid JSON object")


VLM_MIN_DIM = int(os.getenv("AURA_VLM_MIN_DIM", "256"))
VLM_TARGET_DIM = int(os.getenv("AURA_VLM_TARGET_DIM", "384"))


def _preprocess_image(image_bytes: bytes) -> Image.Image:
    """Decode arbitrary image bytes and resize for VLM consumption.

    Policy (aspect-ratio preserving, no letterbox/padding):
    - If the shorter edge is below VLM_MIN_DIM, upscale so the shorter edge
      equals VLM_MIN_DIM (LANCZOS).
    - If the longer edge exceeds VLM_TARGET_DIM, downscale so the longer edge
      equals VLM_TARGET_DIM (LANCZOS).
    - Downscale takes precedence when both conditions would apply (e.g. a
      1x10000 image): the image is first conceptually upscaled then capped.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        rgb = img.convert("RGB")

    w, h = rgb.size
    new_w, new_h = w, h

    short_edge = min(w, h)
    long_edge = max(w, h)

    if short_edge < VLM_MIN_DIM:
        scale_up = VLM_MIN_DIM / short_edge
        new_w = int(w * scale_up)
        new_h = int(h * scale_up)

    effective_long = max(new_w, new_h)
    if effective_long > VLM_TARGET_DIM:
        scale_down = VLM_TARGET_DIM / effective_long
        new_w = max(1, int(new_w * scale_down))
        new_h = max(1, int(new_h * scale_down))

    if (new_w, new_h) != (w, h):
        rgb = rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)

    _log.debug(
        "VLM preprocess: (%d, %d) -> (%d, %d)  min=%d target=%d",
        w, h, new_w, new_h, VLM_MIN_DIM, VLM_TARGET_DIM,
    )
    return rgb


def _image_bytes_to_data_url(image_bytes: bytes) -> str:
    """Convert arbitrary image bytes to a JPEG data URL via _preprocess_image."""
    try:
        rgb = _preprocess_image(image_bytes)
        out = io.BytesIO()
        rgb.save(out, format="JPEG", quality=90)
        encoded = base64.b64encode(out.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"


class OpenAIVLMBackend(InferenceBackend):
    def __init__(
        self,
        *,
        model_id: str,
        endpoint: str | None = None,
        timeout_ms: int | None = None,
        max_tokens: int = 512,
    ) -> None:
        self.model_id = model_id
        self.endpoint = (endpoint or os.getenv("AURA_VLM_ENDPOINT") or "http://127.0.0.1:8000/v1").rstrip("/")
        self.timeout_s = max(0.2, (timeout_ms or int(os.getenv("AURA_VLM_TIMEOUT_MS", "5000"))) / 1000.0)
        self.max_tokens = max_tokens
        self._client: httpx.Client | None = None
        self._ready = False

    def load(self) -> None:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout_s)
        self._ready = self.is_ready()

    def warmup(self) -> None:
        if self._client is None:
            self.load()
        try:
            self.analyze(_WARMUP_IMAGE_PNG_1X1, "Locate any visible object.")
        except Exception:
            self._ready = False
            return
        self._ready = True

    def is_ready(self) -> bool:
        if self._client is None:
            return False
        try:
            response = self._client.get(f"{self.endpoint}/models")
            response.raise_for_status()
            payload = response.json()
            models = payload.get("data", []) if isinstance(payload, dict) else []
            if not isinstance(models, list):
                return False
            if not models:
                return True
            for item in models:
                if isinstance(item, dict) and item.get("id") == self.model_id:
                    return True
            return False
        except Exception:
            return False

    def analyze(self, image: bytes, query: str) -> dict[str, Any]:
        if self._client is None:
            self.load()
        if self._client is None:
            raise RuntimeError("VLM backend client was not initialized")

        image_data_url = _image_bytes_to_data_url(image)
        payload = {
            "model": self.model_id,
            "temperature": 0,
            "top_p": 0.1,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query.strip() or "Describe relevant objects."},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                },
            ],
        }

        response = self._client.post(f"{self.endpoint}/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", []) if isinstance(data, dict) else []
        if not choices:
            raise ValueError("No choices returned by VLM endpoint")

        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        raw_content = message.get("content") if isinstance(message, dict) else None
        parsed = _extract_json_object(raw_content)
        normalized = self._normalize_overlay_response(parsed)
        self._ready = True
        return normalized

    def _normalize_overlay_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        overlays_in = payload.get("overlays", [])
        overlays_out: list[dict[str, Any]] = []

        if isinstance(overlays_in, list):
            for item in overlays_in:
                if not isinstance(item, dict):
                    continue

                bbox = _normalize_bbox(item.get("bbox"), item)
                confidence = _clamp(_to_float(item.get("confidence"), 0.5), 0.0, 1.0)
                label = str(item.get("label") or "unknown").strip() or "unknown"

                ui_layer = str(item.get("ui_layer") or "midground")
                if ui_layer not in _ALLOWED_UI_LAYERS:
                    ui_layer = "midground"

                overlay_type = str(item.get("overlay_type") or "info")
                if overlay_type not in _ALLOWED_OVERLAY_TYPES:
                    overlay_type = "info"

                normalized_overlay: dict[str, Any] = {
                    "bbox": bbox,
                    "label": label,
                    "confidence": confidence,
                    "ui_layer": ui_layer,
                    "overlay_type": overlay_type,
                    "action_required": bool(item.get("action_required", False)),
                }

                if isinstance(item.get("mask_rle"), str) and item["mask_rle"]:
                    normalized_overlay["mask_rle"] = item["mask_rle"]
                if isinstance(item.get("depth_value"), (int, float)):
                    normalized_overlay["depth_value"] = float(item["depth_value"])
                if isinstance(item.get("object_id"), str) and item["object_id"]:
                    normalized_overlay["object_id"] = item["object_id"]

                overlays_out.append(normalized_overlay)

        warnings_raw = payload.get("warnings", [])
        warnings: list[str] = []
        if isinstance(warnings_raw, list):
            warnings = [str(x) for x in warnings_raw if str(x).strip()]

        tracking_state = payload.get("tracking_state")
        result: dict[str, Any] = {
            "request_id": str(payload.get("request_id") or uuid4()),
            "session_id": str(payload.get("session_id") or "unknown"),
            "created_at": str(payload.get("created_at") or datetime.now(UTC).isoformat()),
            "model_version": str(payload.get("model_version") or self.model_id),
            "overlays": overlays_out,
        }

        if isinstance(tracking_state, str) and tracking_state in _ALLOWED_TRACKING_STATES:
            result["tracking_state"] = tracking_state
        if warnings:
            result["warnings"] = warnings
        return result

    def segment(self, image: bytes, bbox: list[float]) -> Any:
        raise NotImplementedError("segment() is not implemented for VLM backends")

    def estimate_depth(self, image: bytes) -> Any:
        raise NotImplementedError("estimate_depth() is not implemented for VLM backends")

    def transcribe(self, audio: bytes) -> str:
        raise NotImplementedError("transcribe() is not implemented for VLM backends")


class QwenVLBackend(OpenAIVLMBackend):
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        model_id: str | None = None,
        timeout_ms: int | None = None,
        max_tokens: int | None = None,
    ) -> None:
        super().__init__(
            model_id=model_id or os.getenv("AURA_VLM_MODEL_ID", "Qwen/Qwen2.5-VL-3B-Instruct-AWQ"),
            endpoint=endpoint,
            timeout_ms=timeout_ms,
            max_tokens=max_tokens or int(os.getenv("AURA_VLM_MAX_TOKENS", "160")),
        )
