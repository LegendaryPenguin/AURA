from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class InferenceBackend(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load model weights and runtime state."""

    @abstractmethod
    def warmup(self) -> None:
        """Run a warmup pass so inference latency is stable."""

    @abstractmethod
    def is_ready(self) -> bool:
        """Return True when backend can serve inference."""

    @abstractmethod
    def analyze(self, image: bytes, query: str) -> dict[str, Any]:
        """Run semantic image analysis and return structured result."""

    @abstractmethod
    def segment(self, image: bytes, bbox: list[float]) -> Any:
        """Generate segmentation output for a region of interest."""

    @abstractmethod
    def estimate_depth(self, image: bytes) -> Any:
        """Generate monocular depth data for the input image."""

    @abstractmethod
    def transcribe(self, audio: bytes) -> str:
        """Convert speech audio bytes into text."""
