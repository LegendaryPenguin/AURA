from __future__ import annotations

from typing import Any

from shared.interfaces.inference_base import InferenceBackend
from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage


class DepthStage(PipelineStage):
    def __init__(self, backend: InferenceBackend, config: dict[str, Any]) -> None:
        self._backend = backend
        self._enabled = bool(config.get("streaming", {}).get("depth_async", True))

    def execute(self, context: PipelineContext) -> PipelineContext:
        if not self._enabled:
            return context
        if context.image is None:
            return context
        try:
            context.depth_map = self._backend.estimate_depth(context.image)
        except Exception:
            context.depth_map = None
        return context
