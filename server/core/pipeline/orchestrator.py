from __future__ import annotations

from typing import Any

from shared.interfaces.inference_base import InferenceBackend
from server.core.pipeline.snapshot_pipeline import SnapshotPipeline
from server.core.pipeline.streaming_pipeline import build_streaming_pipeline
from server.core.pipeline.stages.preprocess import PreprocessStage
from server.core.pipeline.stages.transcribe import TranscribeStage
from server.core.pipeline.stages.analyze import AnalyzeStage
from server.core.pipeline.stages.postprocess import PostprocessStage
from server.core.pipeline.stages.segment import SegmentStage
from server.core.pipeline.stages.depth import DepthStage


def build_snapshot_pipeline(
    backend: InferenceBackend, config: dict[str, Any]
) -> SnapshotPipeline:
    timeouts = config.get("timeouts", {})
    orchestrator_cfg = config.get("orchestrator", {})

    stages = [
        ("preprocess", PreprocessStage(config), timeouts.get("preprocess_ms", 200)),
        ("transcribe", TranscribeStage(backend, config), timeouts.get("transcribe_ms", 800)),
        ("analyze", AnalyzeStage(backend, config), timeouts.get("analyze_ms", 1200)),
        ("postprocess", PostprocessStage(config), timeouts.get("postprocess_ms", 200)),
    ]

    return SnapshotPipeline(
        stages=stages,
        total_timeout_ms=timeouts.get("total_request_timeout_ms", 2000),
        include_timing=orchestrator_cfg.get("include_timing_metadata", False),
    )


def get_pipeline(
    backend: InferenceBackend, config: dict[str, Any]
) -> SnapshotPipeline:
    """Return the correct pipeline for the current orchestrator phase.

    Phases 1-3 use the snapshot pipeline.
    Phases 4-5 will use a streaming pipeline (WS3-E, not yet implemented).
    """
    phase: int = config.get("orchestrator", {}).get("phase", 1)

    if phase <= 3:
        return build_snapshot_pipeline(backend, config)

    semantic_stages = [
        PreprocessStage(config),
        TranscribeStage(backend, config),
        AnalyzeStage(backend, config),
        SegmentStage(backend, config),
        PostprocessStage(config),
    ]
    tracking_stages = [
        SegmentStage(backend, config),
        DepthStage(backend, config),
        PostprocessStage(config),
    ]
    return build_streaming_pipeline(semantic_stages, tracking_stages, config)  # type: ignore[return-value]
