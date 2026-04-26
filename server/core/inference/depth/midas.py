from __future__ import annotations

from server.core.inference.depth.depth_anything import DepthAnythingBackend


class MidasDepthBackend(DepthAnythingBackend):
    """Fallback-compatible MiDaS wrapper."""

