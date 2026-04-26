# WS2-A: Camera Subsystem

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Done`                 |
| **Maturity**| `Verified`             |
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
