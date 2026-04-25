# WS2-C: Frame Capture & Coordinate Mapping

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Done`                 |
| **Owner**   | `Farrell`              |
| **Phase**   | Phase 1                |
| **Stream**  | WS2 — Client Application |

---

## Scope — Owned Files

- `client/src/hooks/useFrameCapture.ts`
- `client/src/services/overlay_mapper.ts`
- `client/src/utils/coord_utils.ts`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `useFrameCapture.ts`: `drawImage` from live video to offscreen canvas → JPEG base64 at 0.85 quality
- `overlay_mapper.ts`: `getBoundingClientRect()` on video element, map normalized coords (0–1) → CSS `left`/`top`/`width`/`height` in px. Use video bounds, not window dimensions.
- `coord_utils.ts`: normalize/denormalize conversions, aspect ratio correction, letterbox/pillarbox compensation

---

## Verification

- [x] Captured frame is a valid JPEG (decodable, correct resolution)
- [x] Overlay mapper: normalized `(0.5, 0.5, 0.2, 0.3)` maps to center of video element regardless of window size
- [x] Coordinate mapping accounts for `object-fit: cover` cropping
- [x] Orientation change triggers coordinate recalculation
- [ ] Unit test: given mock video bounds and normalized bbox, mapper produces correct px values

Remaining:
- Unit test item remains open due strict WS2-C file ownership limiting edits to three implementation files only.
