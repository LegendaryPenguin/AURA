# WS2-G: WebSocket Networking

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Todo`                 |
| **Maturity** | `Planned`            |
| **Owner**   | _Unassigned_           |
| **Phase**   | Phase 4                |
| **Stream**  | WS2 — Client Application |

---

## Scope — Owned Files

- `client/src/services/socket.ts`
- `client/src/hooks/useWebSocket.ts`
- `client/src/hooks/useStreamingSession.ts`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `socket.ts`: WebSocket client — connect, send binary frames, receive JSON overlay messages, auto-reconnect with exponential backoff
- `useWebSocket.ts`: connection lifecycle, message parsing, typed event callbacks
- `useStreamingSession.ts`: session management — open on toggle, close on toggle off, frame rate throttling (configurable, default 15fps), handle reconnect mid-session

---

## Verification

- [ ] Against mock server: WebSocket connects, sends a frame, receives overlay JSON
- [ ] Auto-reconnect fires after disconnect, with exponential backoff
- [ ] Frame throttling: at 15fps config, no more than 15 frames/second are sent
- [ ] Session close sends proper close frame and cleans up resources
- [ ] Unit test: `useWebSocket` hook manages connect/disconnect/message lifecycle

---

## Dependencies

- Upstream tasks: WS3-C, WS3-E
- Downstream tasks: WS2-H, Phase 4 UX
- Runtime dependencies (routes/pipelines/config): `/stream` route availability and session lifecycle.
- Contract dependencies (schemas/interfaces): stream frame and overlay response payload contracts.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS2-G
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

- Trigger conditions: websocket lifecycle instability or stream contract failures.
- Rollback target maturity: `Implemented`
- Blocker owner: WS2 owner
- Re-promotion criteria: websocket verification checklist and integration checks pass.

---

## Residual Risks

- Network instability and browser websocket behavior variance. Owner: WS2. Mitigation: reconnect and timeout coverage.
