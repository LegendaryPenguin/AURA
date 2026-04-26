# WS3-C: WebSocket Route

| Field       | Value                         |
| ----------- | ----------------------------- |
| **Status**  | `Done`                        |
| **Maturity**| `Verified`                    |
| **Owner**   | _Unassigned_                  |
| **Phase**   | Phase 4                       |
| **Stream**  | WS3 — Server API & Pipeline   |

---

## Scope — Owned Files

- `server/api/routes/stream.py`
- `server/api/routes/agents.py`
- `tests/unit/api/test_websocket_route.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `stream.py`: WebSocket `/stream` — accept connection, receive binary frames, pass to streaming pipeline, send JSON overlay results back. Handle disconnect cleanup. Session timeout after 5 minutes of inactivity.
- `agents.py`: `POST /agents/trigger` — accept component identifier, fire agent, return dispatch confirmation. Stretch goal — return mock response if agent subsystem not loaded.

---

## Verification

- [ ] WebSocket connects, accepts binary frame, returns JSON overlay (using mock streaming pipeline)
- [ ] WebSocket handles client disconnect without crash
- [ ] Session timeout fires after 5 minutes of inactivity
- [ ] `/agents/trigger` returns mock response when agent subsystem not loaded
- [ ] Unit test: WebSocket route processes 100 frames without memory leak (measure process RSS)
