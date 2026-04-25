from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class PipelineContext:
    image: bytes | None = None
    query: str | None = None
    bbox: list[float] | None = None
    mask: Any | None = None
    depth_map: Any | None = None
    response: dict[str, Any] | None = None


class PipelineStage(ABC):
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Transform and return the pipeline context."""
