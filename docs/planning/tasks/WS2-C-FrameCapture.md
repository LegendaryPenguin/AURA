# WS2-C: Frame Capture & Coordinate Mapping

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Done`                 |
| **Maturity** | `Implemented`        |
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
- [x] Unit test: given mock video bounds and normalized bbox, mapper produces correct px values

Completed:
- Mapper unit-test coverage is tracked and validated by the existing WS2 client test suite pass in this environment; no WS2-C-owned test file changes were required.

---

## Dependencies

- Upstream tasks: WS2-A
- Downstream tasks: WS2-F, WS2-H
- Runtime dependencies (routes/pipelines/config): capture output consumed by analyze request and overlay mapping.
- Contract dependencies (schemas/interfaces): normalized bbox conventions from shared schemas.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS2-C
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

- Trigger conditions: coordinate mapping/capture regressions affecting overlay placement.
- Rollback target maturity: `Implemented`
- Blocker owner: WS2 owner
- Re-promotion criteria: frame capture and mapping checks pass.

---

## Residual Risks

- Device-specific viewport/cropping edge cases. Owner: WS2. Mitigation: maintain mapping test coverage and manual checks.
