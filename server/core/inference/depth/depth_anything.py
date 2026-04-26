from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from shared.interfaces.inference_base import InferenceBackend


class DepthAnythingBackend(InferenceBackend):
    def __init__(self) -> None:
        self._ready = False

    def load(self) -> None:
        self._ready = True

    def warmup(self) -> None:
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    def analyze(self, image: bytes, query: str) -> dict[str, Any]:
        return {"overlays": []}

    def segment(self, image: bytes, bbox: list[float]) -> Any:
        return None

    def transcribe(self, audio: bytes) -> str:
        return ""

    def estimate_depth(self, image: bytes) -> Any:
        width, height = Image.open(BytesIO(image)).size
        return [[float(y) / max(1, height - 1) for _ in range(width)] for y in range(height)]
