from __future__ import annotations

from server.core.inference.segmentation.sam2 import SAM2SegmentationBackend


class SAMHQSegmentationBackend(SAM2SegmentationBackend):
    """Fallback-compatible SAM-HQ wrapper."""

