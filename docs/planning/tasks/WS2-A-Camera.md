# WS2-A: Camera Subsystem

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Todo`                 |
| **Maturity** | `Planned`            |
| **Owner**   | _Unassigned_           |
| **Phase**   | Phase 2                |
| **Stream**  | WS2 — Client Application |

---

## Scope — Owned Files

- `client/src/components/camera/CameraView.tsx`
- `client/src/components/camera/CameraControls.tsx`
- `client/src/hooks/useCamera.ts`
- `client/src/utils/device_utils.ts`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `CameraView.tsx`: fullscreen `<video>` element, back camera via `getUserMedia`, no UI chrome
- `CameraControls.tsx`: hold-to-scan button, auto-scan toggle, mode selector
- `useCamera.ts`: camera stream lifecycle, back/front switching, cleanup on unmount
- `device_utils.ts`: detect orientation, screen dimensions, safe areas, camera capabilities

---

## Verification

- [ ] Camera opens back-facing camera by default on mobile
- [ ] Video fills viewport with no black bars (object-fit: cover)
- [ ] `orientationchange` event triggers re-render of video element
- [ ] Camera stream is properly released on component unmount
- [ ] Unit test: `useCamera` hook returns a valid MediaStream ref

---

## Dependencies

- Upstream tasks: WS2-H
- Downstream tasks: WS2-B, WS2-F, WS3-B
- Runtime dependencies (routes/pipelines/config): browser camera APIs and capture flow used by snapshot analysis.
- Contract dependencies (schemas/interfaces): no direct schema ownership; must preserve WS2->WS3 API boundaries.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS2-A
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

- Trigger conditions: camera lifecycle instability or regression in capture readiness.
- Rollback target maturity: `Implemented`
- Blocker owner: WS2 owner
- Re-promotion criteria: camera verification checklist passes.

---

## Residual Risks

- Mobile browser differences can cause edge-case camera behavior. Owner: WS2. Mitigation: cross-device manual checks.
