# WS2-B: Audio Subsystem

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Done`                 |
| **Maturity**| `Verified`             |
| **Owner**   | _Unassigned_           |
| **Phase**   | Phase 2                |
| **Stream**  | WS2 — Client Application |

---

## Scope — Owned Files

- `client/src/hooks/useAudioRecorder.ts`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- Hold-to-record: start recording on button down, stop on button up
- Maximum 3-second capture window (auto-stop at limit)
- Encode recorded audio as WAV or WebM base64 string
- Handle microphone permission denial gracefully

---

## Verification

- [ ] Recording starts/stops with button press/release
- [ ] Output is valid base64-encoded audio (decodable, non-empty)
- [ ] 3-second timeout auto-stops recording
- [ ] Permission denial shows user-friendly message, does not crash
- [ ] Unit test: mock MediaRecorder produces expected base64 output
