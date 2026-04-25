# WS1-E: Utilities & Test Fixtures

| Field       | Value                      |
| ----------- | -------------------------- |
| **Status**  | `Todo`                     |
| **Owner**   | _Unassigned_               |
| **Sprint**  | Sprint 0 (Foundation)      |
| **Stream**  | WS1 — Foundation & Contracts |

---

## Scope — Owned Files

- `server/utils/image_utils.py`
- `server/utils/frame_buffer.py`
- `server/utils/config_loader.py`
- `server/utils/logger.py`
- `server/requirements.txt`
- `tests/fixtures/images/*`
- `tests/fixtures/audio/*`
- `tests/fixtures/responses/*`
- `tests/fixtures/mocks/*`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `image_utils.py`: JPEG encode/decode, resize to target dims, base64 encode/decode
- `frame_buffer.py`: circular buffer with configurable max size, drops oldest on overflow, never queues
- `config_loader.py`: load YAML, validate against expected keys, raise clear errors on missing config
- `logger.py`: structured JSON logging with fields: timestamp, stage, result, latency_ms, session_id
- `requirements.txt`: all Python dependencies with pinned versions
- Test fixtures: 5 test images (demo object at various angles, blank image, low-light image), 3 audio clips (clear query, whispered query, silence), 5 golden response payloads, mock implementations for `InferenceBackend`, `PipelineStage`, `TrackerBackend`

---

## Verification

- [ ] `image_utils.py`: round-trip encode→decode produces identical bytes, resize preserves aspect ratio
- [ ] `frame_buffer.py`: overflow drops oldest frame, never blocks, buffer size stays bounded
- [ ] `config_loader.py`: loads valid YAML, rejects missing keys with clear error message
- [ ] `logger.py`: outputs valid JSON to stdout, includes all required fields
- [ ] All mock implementations satisfy their interface contracts (contract tests pass)
