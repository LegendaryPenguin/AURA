from __future__ import annotations

from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage
from server.core.pipeline.streaming_pipeline import StreamingPipeline


class _Stage(PipelineStage):
    def __init__(self, marker: str) -> None:
        self._marker = marker

    def execute(self, context: PipelineContext) -> PipelineContext:
        if context.response is None:
            context.response = {}
        context.response.setdefault("markers", []).append(self._marker)
        return context


def test_streaming_pipeline_semantic_then_tracking() -> None:
    pipeline = StreamingPipeline(
        semantic_stages=[_Stage("semantic")],
        tracking_stages=[_Stage("tracking")],
        requery_interval_ms=60_000,
    )
    first = pipeline.run(PipelineContext(response={}), session_id="s1")
    second = pipeline.run(PipelineContext(response={}), session_id="s1")
    assert first.response["markers"] == ["semantic"]
    assert second.response["markers"] == ["tracking"]
