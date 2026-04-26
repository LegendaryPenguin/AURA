# WS3-F: Validation

| Field       | Value                         |
| ----------- | ----------------------------- |
| **Status**  | `Done`                        |
| **Maturity**| `Verified`                    |
| **Owner**   | `Farrell`                     |
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

## Current Execution Note (2026-04-25)

- Status for this pass: `DoNotPromote`
- Evidence index: `docs/planning/phase01_promotion_evidence.md`
- Changes landed: validator is now enforced by snapshot postprocess runtime.
- Remaining gap: execute full WS3 gate suite with required Python dependencies installed.
