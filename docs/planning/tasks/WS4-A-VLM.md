# WS4-A: VLM Backend


| Field      | Value                      |
| ---------- | -------------------------- |
| **Status** | `Done`                     |
| **Maturity** | `Implemented`           |
| **Owner**  | `Farrell`                  |
| **Phase**  | Phase 1                    |
| **Stream** | WS4 — Inference & Tracking |


---

## Scope — Owned Files

- `server/core/inference/vlm/__init__.py`
- `server/core/inference/vlm/qwen_vl.py`
- `server/core/inference/vlm/llava.py`
- `tests/unit/inference/test_vlm_backends.py`
- `tests/fixtures/images/*` *(co-owned with WS1-E for WS4-A benchmark expansion)*
- `tests/fixtures/vlm_ground_truth.json` *(co-owned with WS1-E for WS4-A accuracy validation)*

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `qwen_vl.py`: implement `InferenceBackend` for Qwen2.5-VL-7B via vLLM OpenAI-compatible API. `analyze(image_bytes, query) → OverlayResponse`. System prompt enforces JSON-only output with normalized coordinates.
- `llava.py`: implement `InferenceBackend` for LLaVA as fallback (smaller, faster, less accurate).
- Prompt engineering: design system prompt requiring JSON-only output, no markdown, normalized coords.
- Benchmark expansion: maintain a 20-image fixture set and `tests/fixtures/vlm_ground_truth.json`, plus recorded/live accuracy harness in `test_vlm_backends.py`.

---

## Verification

- [x] `load()` → `warmup()` → `is_ready()` (mocked / unit; real vLLM is environment-dependent)
- [x] `analyze()` with test fixture image returns valid JSON matching schema (unit tests with `httpx` fakes)
- [x] Bounding box coordinates are within [0,1] range (normalization in unit tests)
- [x] 20-image benchmark dataset + ground-truth file are present (`tests/fixtures/images/*`, `tests/fixtures/vlm_ground_truth.json`)
- [x] Deterministic recorded accuracy harness is implemented and asserts threshold in unit tests
- [ ] Live vLLM accuracy pass-rate >=80% is environment/model dependent (`AURA_VLM_INTEGRATION=1`; enforce with `AURA_VLM_ENFORCE_ACCURACY=1`)
- [ ] Response time under 2 seconds for 7B model — **manual** follow-up
- [x] `llava.py` passes same interface tests (lower accuracy acceptable)
- [x] Unit test: VLM output passes schema validation for fixture-backed paths in `test_vlm_backends.py`

---

## Dependencies

- Upstream tasks: WS1-B, WS1-C, WS3-D
- Downstream tasks: WS3-A, WS3-D, Phase 1/2 capabilities
- Runtime dependencies (routes/pipelines/config): VLM endpoint/model readiness and inference response normalization.
- Contract dependencies (schemas/interfaces): `InferenceBackend` and overlay response contract.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS4-A
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

- Trigger conditions: readiness/accuracy regressions or schema-invalid VLM outputs.
- Rollback target maturity: `Implemented`
- Blocker owner: WS4 owner
- Re-promotion criteria: backend tests plus required live validation checks pass.

---

## Residual Risks

- Live-model quality and latency are environment dependent. Owner: WS4. Mitigation: explicit on-device validation gates.