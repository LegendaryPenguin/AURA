from __future__ import annotations

import time
from typing import Any

from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage


class StreamingPipeline:
    """Lightweight streaming state machine for phases 4-5."""

    def __init__(
        self,
        semantic_stages: list[PipelineStage],
        tracking_stages: list[PipelineStage],
        requery_interval_ms: int = 2500,
    ) -> None:
        self._semantic_stages = semantic_stages
        self._tracking_stages = tracking_stages
        self._requery_interval_ms = requery_interval_ms
        self._last_semantic_by_session: dict[str, float] = {}

    def run(self, context: PipelineContext, session_id: str = "") -> PipelineContext:
        now = time.monotonic() * 1000
        last_semantic = self._last_semantic_by_session.get(session_id, 0.0)
        use_semantic_lane = (now - last_semantic) >= self._requery_interval_ms
        stages = self._semantic_stages if use_semantic_lane else self._tracking_stages
        for stage in stages:
            context = stage.execute(context)
        if context.response is None:
            context.response = {}
        if use_semantic_lane:
            self._last_semantic_by_session[session_id] = now
            context.response["stream_state"] = "semantic"
        else:
            context.response["stream_state"] = "tracking"
        return context


def build_streaming_pipeline(
    semantic_stages: list[PipelineStage],
    tracking_stages: list[PipelineStage],
    config: dict[str, Any],
) -> StreamingPipeline:
    interval = int(config.get("streaming", {}).get("requery_interval_ms", 2500))
    return StreamingPipeline(semantic_stages=semantic_stages, tracking_stages=tracking_stages, requery_interval_ms=interval)
