from __future__ import annotations

import io

from PIL import Image

from server.core.inference.depth.depth_anything import DepthAnythingBackend


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (20, 10), color=(0, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


def test_depth_shape_and_finite_values() -> None:
    backend = DepthAnythingBackend()
    backend.load()
    backend.warmup()
    depth = backend.estimate_depth(_jpeg_bytes())
    assert len(depth) == 10
    assert len(depth[0]) == 20
    assert all(isinstance(value, float) for row in depth for value in row)
