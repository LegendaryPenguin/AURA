from __future__ import annotations

from typing import Any

from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage
from server.utils.image_utils import decode_base64, decode_jpeg, encode_jpeg, resize_with_aspect_ratio


class PreprocessStage(PipelineStage):
    def __init__(self, config: dict[str, Any]) -> None:
        preprocess_cfg = config.get("preprocess", {})
        self._target_width: int = preprocess_cfg.get("target_width", 1280)
        self._target_height: int = preprocess_cfg.get("target_height", 720)
        self._max_image_bytes: int = preprocess_cfg.get("max_image_bytes", 4_194_304)

    def execute(self, context: PipelineContext) -> PipelineContext:
        response = context.response or {}
        image_b64: str | None = response.get("image_base64")
        if not image_b64:
            raise ValueError("Preprocess: missing image_base64 in pipeline context")

        raw_bytes = decode_base64(image_b64)

        if len(raw_bytes) > self._max_image_bytes:
            raise ValueError(
                f"Preprocess: image payload {len(raw_bytes)} bytes exceeds "
                f"limit of {self._max_image_bytes} bytes"
            )

        image = decode_jpeg(raw_bytes)

        resized = resize_with_aspect_ratio(image, self._target_width, self._target_height)
        context.image = encode_jpeg(resized)

        return context
