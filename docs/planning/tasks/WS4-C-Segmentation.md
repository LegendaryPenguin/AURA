# WS4-C: Segmentation Backend

| Field       | Value                            |
| ----------- | -------------------------------- |
| **Status**  | `Todo`                           |
| **Owner**   | _Unassigned_                     |
| **Phase**   | Phase 2                          |
| **Stream**  | WS4 — Inference & Tracking       |

---

## Scope — Owned Files

- `server/core/inference/segmentation/__init__.py`
- `server/core/inference/segmentation/sam2.py`
- `server/core/inference/segmentation/sam_hq.py`
- `tests/unit/inference/test_segmentation_backends.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `sam2.py`: implement `InferenceBackend` for SAM2-Large. Two modes:
  - Single-frame: `segment(image, bbox) → mask` — given a bounding box prompt, produce a pixel-accurate mask
  - Video init: `init_video_predictor(image, mask) → predictor_state` — initialize tracking from a mask
- `sam_hq.py`: implement same interface with SAM-HQ for higher-quality masks (optional swap)

---

## Verification

- [ ] `load()` → `warmup()` → `is_ready()` returns True
- [ ] `segment()` with test image and known-good bbox returns a mask of expected dimensions
- [ ] Mask is a binary array (0/1 or 0/255) matching image dimensions
- [ ] Mask covers >50% of the bounding box area (not returning empty mask)
- [ ] Response time under 200ms for single-frame segmentation
- [ ] Unit test: mask output dimensions match input image dimensions
