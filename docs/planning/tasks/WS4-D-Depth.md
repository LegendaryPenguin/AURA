# WS4-D: Depth Backend

| Field       | Value                            |
| ----------- | -------------------------------- |
| **Status**  | `Todo`                           |
| **Owner**   | _Unassigned_                     |
| **Phase**   | Phase 5                          |
| **Stream**  | WS4 — Inference & Tracking       |

---

## Scope — Owned Files

- `server/core/inference/depth/__init__.py`
- `server/core/inference/depth/depth_anything.py`
- `server/core/inference/depth/midas.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `depth_anything.py`: implement `InferenceBackend` for Depth Anything v2. `estimate(image) → depth_map` — returns H x W float array of relative depth values.
- `midas.py`: implement same interface with MiDaS as fallback.

---

## Verification

- [ ] `load()` → `warmup()` → `is_ready()` returns True
- [ ] `estimate()` returns array matching input image dimensions (H x W)
- [ ] Depth values are finite floats (no NaN, no Inf)
- [ ] Near objects have lower depth values than far objects (sanity check with known scene)
- [ ] Response time under 100ms per frame
- [ ] Unit test: depth map output shape matches input shape, values in valid range
