from __future__ import annotations

from typing import Any

from shared.interfaces.inference_base import InferenceBackend
from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage


class SegmentStage(PipelineStage):
    def __init__(self, backend: InferenceBackend, config: dict[str, Any]) -> None:
        self._backend = backend
        self._enabled = bool(config.get("streaming", {}).get("enable_segment", True))

    def execute(self, context: PipelineContext) -> PipelineContext:
        if not self._enabled:
            return context
        if context.image is None or context.bbox is None:
            return context
        try:
            context.mask = self._backend.segment(context.image, context.bbox)
        except Exception:
            # Keep streaming resilient; segmentation is best-effort.
            context.mask = None
        return context
