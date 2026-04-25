from __future__ import annotations

from typing import Any

from shared.interfaces.inference_base import InferenceBackend
from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage


class AnalyzeStage(PipelineStage):
    def __init__(self, backend: InferenceBackend, config: dict[str, Any]) -> None:
        self._backend = backend
        self._config = config

    def execute(self, context: PipelineContext) -> PipelineContext:
        if context.image is None:
            raise ValueError("Analyze: no preprocessed image in pipeline context")

        query = context.query or ""
        if not query:
            snapshot_cfg = self._config.get("snapshot", {})
            query = snapshot_cfg.get("default_query", "What am I looking at?")

        result = self._backend.analyze(context.image, query)
        context.response = context.response or {}
        context.response["vlm_result"] = result

        return context
