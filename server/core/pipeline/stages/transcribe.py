from __future__ import annotations

import logging
from typing import Any

from shared.interfaces.inference_base import InferenceBackend
from shared.interfaces.pipeline_stage import PipelineContext, PipelineStage

_log = logging.getLogger(__name__)


class TranscribeStage(PipelineStage):
    def __init__(self, backend: InferenceBackend, config: dict[str, Any]) -> None:
        self._backend = backend
        snapshot_cfg = config.get("snapshot", {})
        self._default_query: str = snapshot_cfg.get("default_query", "What am I looking at?")

    def execute(self, context: PipelineContext) -> PipelineContext:
        response = context.response or {}
        audio_b64: str | None = response.get("audio_base64")

        if not audio_b64:
            context.query = context.query or self._default_query
            return context

        from server.utils.image_utils import decode_base64

        audio_bytes = decode_base64(audio_b64)

        try:
            transcript = self._backend.transcribe(audio_bytes)
        except Exception:
            _log.warning("Transcription failed, falling back to default query")
            transcript = ""

        context.query = transcript if transcript else self._default_query
        return context
