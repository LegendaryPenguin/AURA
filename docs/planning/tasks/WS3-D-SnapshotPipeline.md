# WS3-D: Snapshot Pipeline & Stages

| Field       | Value                         |
| ----------- | ----------------------------- |
| **Status**  | `Done`                        |
| **Owner**   | `Farrell`                     |
| **Phase**   | Phase 1                       |
| **Stream**  | WS3 — Server API & Pipeline   |

---

## Scope — Owned Files

- `server/core/pipeline/orchestrator.py`
- `server/core/pipeline/snapshot_pipeline.py`
- `server/core/pipeline/stages/__init__.py`
- `server/core/pipeline/stages/preprocess.py`
- `server/core/pipeline/stages/transcribe.py`
- `server/core/pipeline/stages/analyze.py`
- `server/core/pipeline/stages/postprocess.py`
- `server/core/pipeline/__init__.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `orchestrator.py`: read current phase from config, return correct pipeline instance (snapshot or streaming)
- `snapshot_pipeline.py`: chain stages in order — preprocess → transcribe → analyze → segment → postprocess. Per-stage timeouts from `config/pipeline.yaml`. Return 408 if total exceeds timeout.
- `preprocess.py`: decode base64, validate JPEG header, resize to model input dims. Reject non-JPEG.
- `transcribe.py`: call audio backend's `transcribe()`. Fall back to default query from config on failure.
- `analyze.py`: call VLM backend's `analyze()` with preprocessed image and query.
- `postprocess.py`: merge all stage outputs into `PipelineContext`, run validation, format final payload matching `overlay_response.json`.

Each stage implements the `PipelineStage` interface. Each stage receives and returns a `PipelineContext`.

---

## Verification

- [x] With mock backends: snapshot pipeline returns valid overlay response for test image
- [x] Preprocess rejects non-JPEG input with clear error
- [x] Preprocess resizes to configured dimensions
- [x] Transcribe falls back to default query when audio is empty
- [x] Per-stage timeout fires and returns 408 (test with a mock that sleeps)
- [x] Postprocess validates output against schema and rejects malformed VLM output
- [x] Unit test per stage: each stage independently transforms `PipelineContext` correctly
