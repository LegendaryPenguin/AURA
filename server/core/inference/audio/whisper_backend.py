from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class WhisperBackend:
    """Speech-to-text using OpenAI Whisper via the local `whisper` library.

    Falls back gracefully when the whisper package or model files are missing,
    allowing the server to boot with degraded audio support.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        max_duration_seconds: int = 12,
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._max_duration_seconds = max_duration_seconds
        self._model: Any = None
        self._ready = False

    def load(self) -> None:
        try:
            import whisper  # type: ignore[import-untyped]

            device = self._device
            if device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"

            self._model = whisper.load_model(self._model_size, device=device)
            self._ready = True
            logger.info("Whisper '%s' loaded on %s", self._model_size, device)
        except ImportError:
            logger.warning(
                "whisper package not installed; audio transcription will use fallback"
            )
            self._ready = False
        except Exception as exc:
            logger.warning("Whisper load failed: %s", exc)
            self._ready = False

    def is_ready(self) -> bool:
        return self._ready

    def transcribe(self, audio_bytes: bytes) -> str:
        if not self._ready or self._model is None:
            raise RuntimeError("Whisper backend not loaded")

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            result = self._model.transcribe(
                tmp.name,
                language="en",
                fp16=False,
            )

        text = result.get("text", "").strip()
        logger.info("Whisper transcription: %r (%d chars)", text[:80], len(text))
        return text
