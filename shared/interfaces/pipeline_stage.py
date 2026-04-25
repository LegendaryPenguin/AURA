from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class PipelineContext:
    """
    Field contract for pipeline stage I/O:

    Route -> PreprocessStage:
        response["image_base64"]: base64 JPEG string
        response["audio_base64"]: base64 audio string or None
        query: user's text query or None

    PreprocessStage -> AnalyzeStage:
        image: resized JPEG bytes

    TranscribeStage -> AnalyzeStage:
        query: transcribed text or default

    AnalyzeStage -> PostprocessStage:
        response["vlm_result"]: dict from VLM backend

    PostprocessStage -> Route:
        response: final overlay response dict
    """

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
