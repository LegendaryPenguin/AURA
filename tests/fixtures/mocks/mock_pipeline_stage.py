from __future__ import annotations

from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage


class MockPipelineStage(PipelineStage):
    def __init__(self, stage_name: str = "mock-stage") -> None:
        self.stage_name = stage_name

    def execute(self, context: PipelineContext) -> PipelineContext:
        response = context.response or {}
        response["last_stage"] = self.stage_name
        context.response = response
        return context
