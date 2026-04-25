# WS2-G: WebSocket Networking

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Todo`                 |
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
