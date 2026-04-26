from __future__ import annotations

import io

from PIL import Image

from server.core.inference.segmentation.sam2 import SAM2SegmentationBackend


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(255, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


def test_segmentation_mask_dimensions() -> None:
    backend = SAM2SegmentationBackend()
    backend.load()
    backend.warmup()
    mask = backend.segment(_jpeg_bytes(), [0.25, 0.25, 0.5, 0.5])
    assert len(mask) == 32
    assert len(mask[0]) == 32
