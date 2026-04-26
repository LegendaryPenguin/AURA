from __future__ import annotations

import logging
from typing import Any

from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage

logger = logging.getLogger(__name__)


class SegmentStage(PipelineStage):
    """Runs SAM2 segmentation on the analyzed image using the VLM's bbox output.

    Expects context.response["vlm_result"]["overlays"] to contain bbox data from
    the AnalyzeStage. Attaches mask RLE data to each overlay.
    """

    def __init__(self, segmentation_backend: Any, config: dict[str, Any]) -> None:
        self._backend = segmentation_backend
        self._config = config

    def execute(self, context: PipelineContext) -> PipelineContext:
        response = context.response or {}
        vlm_result = response.get("vlm_result", {})
        overlays = vlm_result.get("overlays", [])

        if not context.image:
            logger.warning("SegmentStage: no image in context, skipping")
            return context

        if not overlays:
            logger.info("SegmentStage: no overlays to segment, passing through")
            return context

        for overlay in overlays:
            bbox_raw = overlay.get("bbox")
            if not bbox_raw:
                continue

            if isinstance(bbox_raw, dict):
                bbox_list = [
                    bbox_raw.get("x", 0),
                    bbox_raw.get("y", 0),
                    bbox_raw.get("width", 0),
                    bbox_raw.get("height", 0),
                ]
            elif isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) >= 4:
                bbox_list = list(bbox_raw[:4])
            else:
                continue

            try:
                seg_result = self._backend.segment(context.image, bbox_list)
                overlay["mask_rle"] = seg_result.get("mask_rle")
                overlay["segment_score"] = seg_result.get("score", 0.0)
            except Exception as exc:
                logger.warning(
                    "SegmentStage: segmentation failed for bbox %s: %s",
                    bbox_raw,
                    exc,
                )

        response["vlm_result"] = vlm_result
        context.response = response
        return context
