"""Tests for Whisper audio transcription backend."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_whisper_backend_instantiation():
    from server.core.inference.audio.whisper_backend import WhisperBackend

    backend = WhisperBackend(model_size="base", device="cpu")
    assert not backend.is_ready()


def test_whisper_backend_graceful_when_whisper_not_installed():
    from server.core.inference.audio.whisper_backend import WhisperBackend

    backend = WhisperBackend()
    with patch.dict("sys.modules", {"whisper": None}):
        backend.load()
    assert not backend.is_ready()


def test_whisper_backend_transcribe_raises_when_not_loaded():
    from server.core.inference.audio.whisper_backend import WhisperBackend

    backend = WhisperBackend()
    with pytest.raises(RuntimeError, match="not loaded"):
        backend.transcribe(b"fake audio data")


def test_whisper_backend_load_with_mock():
    from server.core.inference.audio.whisper_backend import WhisperBackend

    mock_whisper = MagicMock()
    mock_model = MagicMock()
    mock_whisper.load_model.return_value = mock_model

    with patch.dict("sys.modules", {"whisper": mock_whisper}):
        with patch("torch.cuda.is_available", return_value=False):
            backend = WhisperBackend(model_size="tiny", device="auto")
            backend.load()

    assert backend.is_ready()
