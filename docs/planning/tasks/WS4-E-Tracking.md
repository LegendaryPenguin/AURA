# WS4-E: Tracking System

| Field       | Value                            |
| ----------- | -------------------------------- |
| **Status**  | `Done`                           |
| **Maturity**| `Verified`                       |
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
