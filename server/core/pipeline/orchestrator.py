from __future__ import annotations

import logging
from typing import Any

from shared.interfaces.inference_base import InferenceBackend
from server.core.pipeline.snapshot_pipeline import SnapshotPipeline
from server.core.pipeline.stages.preprocess import PreprocessStage
from server.core.pipeline.stages.transcribe import TranscribeStage
from server.core.pipeline.stages.analyze import AnalyzeStage
from server.core.pipeline.stages.segment import SegmentStage
from server.core.pipeline.stages.postprocess import PostprocessStage

logger = logging.getLogger(__name__)


def build_snapshot_pipeline(
    backend: InferenceBackend,
    config: dict[str, Any],
    segmentation_backend: Any = None,
    whisper_backend: Any = None,
) -> SnapshotPipeline:
    timeouts = config.get("timeouts", {})
    orchestrator_cfg = config.get("orchestrator", {})
    phase: int = orchestrator_cfg.get("phase", 1)

    stages: list[tuple[str, Any, float]] = [
        ("preprocess", PreprocessStage(config), timeouts.get("preprocess_ms", 200)),
        ("transcribe", TranscribeStage(backend, config, whisper_backend=whisper_backend), timeouts.get("transcribe_ms", 800)),
        ("analyze", AnalyzeStage(backend, config), timeouts.get("analyze_ms", 1200)),
    ]

    if phase >= 2 and segmentation_backend is not None:
        stages.append(
            ("segment", SegmentStage(segmentation_backend, config), timeouts.get("segment_ms", 300))
        )
        logger.info("Pipeline includes segmentation stage for phase %d", phase)

    stages.append(
        ("postprocess", PostprocessStage(config), timeouts.get("postprocess_ms", 200))
    )

    return SnapshotPipeline(
        stages=stages,
        total_timeout_ms=timeouts.get("total_request_timeout_ms", 2000),
        include_timing=orchestrator_cfg.get("include_timing_metadata", False),
    )


def get_pipeline(
    backend: InferenceBackend,
    config: dict[str, Any],
    segmentation_backend: Any = None,
    whisper_backend: Any = None,
) -> SnapshotPipeline:
    """Return the correct pipeline for the current orchestrator phase.

    Phases 1-3 use the snapshot pipeline.
    Phases 4-5 will use a streaming pipeline (WS3-E, not yet implemented).
    """
    phase: int = config.get("orchestrator", {}).get("phase", 1)

    if phase <= 3:
        return build_snapshot_pipeline(backend, config, segmentation_backend, whisper_backend)

    raise NotImplementedError(
        f"Streaming pipeline for phase {phase} is not yet implemented (see WS3-E)"
    )
