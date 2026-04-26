from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from shared.interfaces.inference_base import InferenceBackend


class SAM2SegmentationBackend(InferenceBackend):
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

    def transcribe(self, audio: bytes) -> str:
        return ""

    def estimate_depth(self, image: bytes) -> Any:
        return None

    def segment(self, image: bytes, bbox: list[float]) -> Any:
        width, height = Image.open(BytesIO(image)).size
        x, y, w, h = bbox
        mask = [[0 for _ in range(width)] for _ in range(height)]
        x0 = max(0, int(x * width))
        y0 = max(0, int(y * height))
        x1 = min(width, int((x + w) * width))
        y1 = min(height, int((y + h) * height))
        for j in range(y0, y1):
            row = mask[j]
            for i in range(x0, x1):
                row[i] = 1
        return mask
