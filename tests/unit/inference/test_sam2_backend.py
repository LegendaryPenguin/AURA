"""Tests for SAM2 segmentation backend."""
from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image


def _make_test_jpeg(w: int = 100, h: int = 80) -> bytes:
    img = Image.fromarray(np.random.randint(0, 255, (h, w, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_sam2_backend_instantiation():
    from server.core.inference.segmentation.sam2_backend import SAM2Backend

    backend = SAM2Backend(checkpoint_path="nonexistent.pt")
    assert not backend.is_ready()


def test_sam2_backend_load_graceful_when_library_missing():
    from server.core.inference.segmentation.sam2_backend import SAM2Backend

    backend = SAM2Backend(checkpoint_path="nonexistent.pt")
    backend.load()
    assert not backend.is_ready()


def test_sam2_fallback_mask_shape():
    from server.core.inference.segmentation.sam2_backend import SAM2Backend

    backend = SAM2Backend()
    backend.load()

    jpeg = _make_test_jpeg(200, 150)
    result = backend.segment(jpeg, [0.1, 0.2, 0.3, 0.4])

    assert "mask_rle" in result
    assert "bbox" in result
    assert "score" in result
    assert result["width"] == 200
    assert result["height"] == 150
    assert isinstance(result["mask_rle"]["counts"], list)
    assert result["mask_rle"]["size"] == [150, 200]


def test_sam2_fallback_mask_covers_bbox_region():
    from server.core.inference.segmentation.sam2_backend import SAM2Backend

    backend = SAM2Backend()
    backend.load()

    jpeg = _make_test_jpeg(100, 100)
    result = backend.segment(jpeg, [0.0, 0.0, 1.0, 1.0])

    assert result["score"] == 0.85


def test_sam2_rle_encoding_roundtrip():
    from server.core.inference.segmentation.sam2_backend import SAM2Backend

    mask = np.zeros((10, 10), dtype=bool)
    mask[2:5, 3:7] = True
    rle = SAM2Backend._mask_to_rle(mask)
    assert rle["size"] == [10, 10]
    assert isinstance(rle["counts"], list)
    assert sum(rle["counts"]) == 100
