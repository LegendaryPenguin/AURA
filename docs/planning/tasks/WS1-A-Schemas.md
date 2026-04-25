# WS1-A: Schemas & TypeScript Types


| Field      | Value                        |
| ---------- | ---------------------------- |
| **Status** | `Done`                       |
| **Maturity** | `Implemented`             |
| **Owner**  | `Farrell`                    |
| **Sprint** | Sprint 0 (Foundation)        |
| **Stream** | WS1 — Foundation & Contracts |


---

## Scope — Owned Files

- `shared/schemas/overlay_response.json`
- `shared/schemas/analysis_request.json`
- `shared/schemas/stream_frame.json`
- `shared/schemas/tracking_state.json`
- `shared/schemas/types.ts`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- Define the JSON Schema for every message that crosses a workstream boundary
- Auto-generate TypeScript types from JSON schemas (use `json-schema-to-typescript` or equivalent)
- Include all overlay types: `diagnostic`, `hazard`, `info`, `reference`
- Include all required fields: `bbox` (normalized 0–1), `label`, `confidence`, `ui_layer`, `overlay_type`, `action_required`, `mask_rle` (optional), `depth_value` (optional)

---

## Verification

- Every schema passes `jsonschema` self-validation
- TypeScript types compile with zero errors
- 5 golden response fixtures validate against the schema
- 3 intentionally malformed fixtures are correctly rejected

---

## Dependencies

- Upstream tasks: None
- Downstream tasks: WS2-F, WS3-B, WS3-F
- Runtime dependencies (routes/pipelines/config): Schema consumers must use canonical request/response field names.
- Contract dependencies (schemas/interfaces): `shared/schemas/*.json`, `shared/schemas/types.ts`

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS1-A
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

- Trigger conditions: Contract-breaking schema change or failed contract gate.
- Rollback target maturity: `Implemented`
- Blocker owner: WS1 owner
- Re-promotion criteria: Contract tests and dependent task checks pass.

---

## Residual Risks

- Schema evolution can outpace downstream adoption. Owner: WS1. Mitigation: append-only schema policy plus contract gates.