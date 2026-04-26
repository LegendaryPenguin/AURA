from __future__ import annotations

from typing import Any

from shared.interfaces.inference_base import InferenceBackend


class WhisperAudioBackend(InferenceBackend):
    def __init__(self) -> None:
        self._ready = False

    def load(self) -> None:
        self._ready = True

    def warmup(self) -> None:
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    def analyze(self, image: bytes, query: str) -> dict[str, Any]:
        return {"overlays": [], "warnings": ["audio_backend_analyze_not_supported"]}

    def segment(self, image: bytes, bbox: list[float]) -> Any:
        return None

    def estimate_depth(self, image: bytes) -> Any:
        return None

    def transcribe(self, audio: bytes) -> str:
        if not audio or not audio.strip(b"\x00"):
            return ""
        return "transcription_unavailable_local_stub"
