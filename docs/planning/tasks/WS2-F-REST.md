# WS2-F: REST Networking

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Done`                 |
| **Maturity** | `Implemented`        |
| **Owner**   | Farrell                |
| **Phase**   | Phase 1                |
| **Stream**  | WS2 — Client Application |

---

## Scope — Owned Files

- `client/src/services/api.ts`
- `client/src/hooks/useSnapshotAnalysis.ts`
- `client/src/types/overlay.ts`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `api.ts`: typed fetch wrappers for `POST /analyze`, `GET /health`. Timeout at 5 seconds. Parse and validate response against TypeScript types.
- `useSnapshotAnalysis.ts`: hook that coordinates frame capture + audio recording + API call. Returns overlay response or error state.
- `overlay.ts`: TypeScript types imported from `shared/schemas/types.ts`

---

## Verification

- [x] Against mock server: `POST /analyze` with test image returns valid overlay response
- [x] Against mock server: `GET /health` returns model status
- [x] 5-second timeout fires correctly — scan animation stops, error message shown
- [x] HTTP errors (422, 429, 408, 500) are handled with user-friendly messages
- [x] Unit test: `useSnapshotAnalysis` hook state machine transitions: idle → loading → success/error

---

## Dependencies

- Upstream tasks: WS1-A, WS3-B
- Downstream tasks: WS2-H
- Runtime dependencies (routes/pipelines/config): `/analyze` and `/health` behavior and proxy mode alignment.
- Contract dependencies (schemas/interfaces): analyze request/response payload contracts.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS2-F
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

- Trigger conditions: API contract mismatch or networking regressions in analyze flow.
- Rollback target maturity: `Implemented`
- Blocker owner: WS2 owner
- Re-promotion criteria: API/hook tests plus integration gate pass.

---

## Residual Risks

- Environment proxy and TLS mode mismatches can break local flow. Owner: WS2. Mitigation: mode-specific validation checks.
