# WS4-B: Audio Backend

| Field       | Value                            |
| ----------- | -------------------------------- |
| **Status**  | `Todo`                           |
| **Owner**   | _Unassigned_                     |
| **Phase**   | Phase 2                          |
| **Stream**  | WS4 — Inference & Tracking       |

---

## Scope — Owned Files

- `server/core/inference/audio/__init__.py`
- `server/core/inference/audio/whisper.py`
- `tests/unit/inference/test_audio_backend.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `whisper.py`: implement `InferenceBackend` for Whisper-base. `transcribe(audio_bytes) → str`. Handle empty audio (return empty string). Handle noise-only audio gracefully.

---

## Verification

- [ ] `load()` → `warmup()` → `is_ready()` returns True
- [ ] `transcribe()` with clear speech audio fixture returns correct text
- [ ] `transcribe()` with silence returns empty string
- [ ] `transcribe()` with noise returns empty string (not hallucinated text)
- [ ] Response time under 1 second for 3-second audio clip
- [ ] Unit test: transcription output is a valid UTF-8 string
