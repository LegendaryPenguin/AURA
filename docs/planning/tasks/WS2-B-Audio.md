# WS2-B: Audio Subsystem

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Todo`                 |
| **Maturity** | `Planned`            |
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

---

## Dependencies

- Upstream tasks: WS2-A
- Downstream tasks: WS2-F, WS4-B
- Runtime dependencies (routes/pipelines/config): browser microphone APIs and encode path consumed by analyze request.
- Contract dependencies (schemas/interfaces): audio payload fields in analyze request schema.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS2-B
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

- Trigger conditions: recording regressions or invalid/empty audio output.
- Rollback target maturity: `Implemented`
- Blocker owner: WS2 owner
- Re-promotion criteria: audio verification checklist passes.

---

## Residual Risks

- Permissions and codec variability across browsers/devices. Owner: WS2. Mitigation: fallback handling and compatibility tests.
