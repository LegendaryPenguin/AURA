# WS4-B: Audio Backend

| Field       | Value                            |
| ----------- | -------------------------------- |
| **Status**  | `Todo`                           |
| **Maturity** | `Planned`                      |
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

---

## Dependencies

- Upstream tasks: WS1-B, WS1-C
- Downstream tasks: WS3-D, WS2-B, Phase 2 flow
- Runtime dependencies (routes/pipelines/config): audio backend loading and transcription path in snapshot pipeline.
- Contract dependencies (schemas/interfaces): `InferenceBackend.transcribe` behavior contract.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS4-B
  MaturityBefore: <level>
  MaturityAfter: <level>
  ChangeSummary: <what changed>
  GatesRun:
    - <test/check>
  EvidenceLinks:
    - <path/log/artifact>
  DependenciesClosed: <yes/no + note>
  ResidualRisk: <risk + owner>
  RollbackRequired: <Yes/No>
  Signoff:
    - <workstream/owner>
```

---

## Rollback

- Trigger conditions: transcription instability or latency regressions.
- Rollback target maturity: `Implemented`
- Blocker owner: WS4 owner
- Re-promotion criteria: audio backend verification checklist passes.

---

## Residual Risks

- Noisy-environment behavior may vary across hardware. Owner: WS4. Mitigation: include robust noise/silence fixtures.
