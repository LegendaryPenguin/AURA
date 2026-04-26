"""Tests for the SegmentStage pipeline stage."""
from __future__ import annotations

import io
from unittest.mock import MagicMock

import numpy as np
from PIL import Image

from server.core.pipeline.stages.segment import SegmentStage
from shared.interfaces.pipeline_stage import PipelineContext


def _make_test_jpeg(w: int = 100, h: int = 80) -> bytes:
    img = Image.fromarray(np.random.randint(0, 255, (h, w, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_segment_stage_passes_through_when_no_image():
    backend = MagicMock()
    stage = SegmentStage(backend, {})

    ctx = PipelineContext(response={"vlm_result": {"overlays": [{"bbox": [0.1, 0.2, 0.3, 0.4]}]}})
    result = stage.execute(ctx)

    backend.segment.assert_not_called()
    assert result is ctx


def test_segment_stage_passes_through_when_no_overlays():
    backend = MagicMock()
    stage = SegmentStage(backend, {})

    ctx = PipelineContext(image=_make_test_jpeg(), response={"vlm_result": {"overlays": []}})
    result = stage.execute(ctx)

    backend.segment.assert_not_called()


def test_segment_stage_calls_backend_per_overlay():
    backend = MagicMock()
    backend.segment.return_value = {"mask_rle": {"counts": [1, 2], "size": [80, 100]}, "score": 0.95}

    stage = SegmentStage(backend, {})
    ctx = PipelineContext(
        image=_make_test_jpeg(),
        response={
            "vlm_result": {
                "overlays": [
                    {"bbox": [0.1, 0.2, 0.3, 0.4], "label": "test"},
                    {"bbox": [0.5, 0.5, 0.2, 0.2], "label": "test2"},
                ]
            }
        },
    )

    result = stage.execute(ctx)
    assert backend.segment.call_count == 2

    overlays = result.response["vlm_result"]["overlays"]
    assert overlays[0]["mask_rle"] == {"counts": [1, 2], "size": [80, 100]}
    assert overlays[0]["segment_score"] == 0.95
    assert overlays[1]["mask_rle"] is not None


def test_segment_stage_handles_backend_error_gracefully():
    backend = MagicMock()
    backend.segment.side_effect = RuntimeError("SAM2 error")

    stage = SegmentStage(backend, {})
    ctx = PipelineContext(
        image=_make_test_jpeg(),
        response={"vlm_result": {"overlays": [{"bbox": [0.1, 0.2, 0.3, 0.4]}]}},
    )

    result = stage.execute(ctx)
    assert "mask_rle" not in result.response["vlm_result"]["overlays"][0]
