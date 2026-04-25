from __future__ import annotations

from typing import Any

from shared.interfaces.inference_base import InferenceBackend


class MockInferenceBackend(InferenceBackend):
    def __init__(self) -> None:
        self._ready = False

    def load(self) -> None:
        self._ready = True

    def warmup(self) -> None:
        return None

    def is_ready(self) -> bool:
        return self._ready

    def analyze(self, image: bytes, query: str) -> dict[str, Any]:
        return {"query": query, "bytes": len(image), "overlays": []}

    def segment(self, image: bytes, bbox: list[float]) -> Any:
        return {"bbox": bbox, "mask": [[1, 1], [1, 1]]}

    def estimate_depth(self, image: bytes) -> Any:
        return {"depth_map": [[0.1, 0.2], [0.3, 0.4]], "bytes": len(image)}

    def transcribe(self, audio: bytes) -> str:
        if not audio:
            return ""
        return "mock transcript"
