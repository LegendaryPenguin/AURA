from __future__ import annotations

from server.core.inference.audio.whisper import WhisperAudioBackend


def test_whisper_backend_lifecycle_and_transcribe() -> None:
    backend = WhisperAudioBackend()
    backend.load()
    backend.warmup()
    assert backend.is_ready()
    assert backend.transcribe(b"") == ""
    assert isinstance(backend.transcribe(b"audio"), str)
