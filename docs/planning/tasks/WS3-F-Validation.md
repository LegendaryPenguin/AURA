# WS3-F: Validation

| Field       | Value                         |
| ----------- | ----------------------------- |
| **Status**  | `Done`                        |
| **Maturity** | `Implemented`               |
| **Owner**   | Farrell                       |
| **Phase**   | Phase 1                       |
| **Stream**  | WS3 — Server API & Pipeline   |

---

## Scope — Owned Files

- `server/core/validation/__init__.py`
- `server/core/validation/schemas.py`
- `server/core/validation/validators.py`
- `tests/unit/pipeline/test_validation.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `schemas.py`: Pydantic models matching `shared/schemas/overlay_response.json`. Strict field types, enums for `overlay_type` and `ui_layer`.
- `validators.py`: validate VLM raw output against JSON schema. Reject if coordinates out of [0,1] bounds. Reject if `ui_layer` not in allowed enum. Reject if confidence below configurable floor. Return `None` on rejection — never pass malformed data.

---

## Verification

- [x] Valid golden response fixtures pass validation
- [x] Coordinates outside [0,1] are rejected
- [x] Missing required fields are rejected
- [x] Invalid `overlay_type` enum values are rejected
- [x] Low-confidence responses below threshold are rejected
- [x] Rejected responses return `None`, not an exception
- [x] Unit test: 5 valid and 5 invalid fixtures are correctly accepted/rejected

---

## Dependencies

- Upstream tasks: WS1-A, WS3-D
- Downstream tasks: WS3-B, Phase promotion gates
- Runtime dependencies (routes/pipelines/config): validation behavior in postprocess and route response shaping.
- Contract dependencies (schemas/interfaces): overlay response schema and enum bounds.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS3-F
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

- Trigger conditions: false accepts/rejects in validation behavior.
- Rollback target maturity: `Implemented`
- Blocker owner: WS3 owner
- Re-promotion criteria: validation fixture tests pass and downstream checks are green.

---

## Residual Risks

- Threshold tuning can over-filter valid low-confidence results. Owner: WS3. Mitigation: tune with benchmark datasets.
