# WS2-F: REST Networking

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Done`                 |
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
