# WS4-E: Tracking System

| Field       | Value                            |
| ----------- | -------------------------------- |
| **Status**  | `Todo`                           |
| **Maturity** | `Planned`                      |
| **Owner**   | _Unassigned_                     |
| **Phase**   | Phase 4                          |
| **Stream**  | WS4 — Inference & Tracking       |

---

## Scope — Owned Files

- `server/core/tracking/__init__.py`
- `server/core/tracking/tracker.py`
- `server/core/tracking/track_manager.py`
- `tests/unit/tracking/test_tracker_system.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `tracker.py`: wrap SAM2's VideoPredictor. State machine: `IDLE → SEEDED → TRACKING → LOST`. Expose `seed(mask)`, `propagate(frame) → mask`, `reset()`. Transition to `LOST` when mask IoU drops below threshold. Auto-reset after configurable timeout in `LOST` state.
- `track_manager.py`: maintain dict of `session_id → tracker`. Create tracker on WebSocket connect, destroy on disconnect. Idle session timeout (configurable, default 5 minutes). Explicit memory cleanup on destroy to prevent OOM.

---

## Verification

- [ ] State machine: IDLE → seed → SEEDED → propagate → TRACKING (correct transitions)
- [ ] State machine: TRACKING → propagate returns low IoU → LOST (correct detection)
- [ ] State machine: reset() from any state → IDLE
- [ ] Track manager: create and retrieve tracker by session ID
- [ ] Track manager: destroy tracker releases memory (check with `gc.get_referrers`)
- [ ] Track manager: idle timeout fires and destroys tracker
- [ ] Unit test: process 50 frames through tracker without memory growth

---

## Dependencies

- Upstream tasks: WS4-C, WS3-E
- Downstream tasks: WS3-C, WS2-G, Phase 4
- Runtime dependencies (routes/pipelines/config): tracker state machine and session lifecycle.
- Contract dependencies (schemas/interfaces): tracker backend state and propagation contract.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS4-E
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

- Trigger conditions: tracker state or memory lifecycle regressions.
- Rollback target maturity: `Implemented`
- Blocker owner: WS4 owner
- Re-promotion criteria: tracking state-machine and memory checks pass.

---

## Residual Risks

- Long-session tracking drift and memory pressure under production load. Owner: WS4. Mitigation: stress tests and timeout cleanup gates.
