# WS2-D: Overlay Rendering

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Done`                 |
| **Owner**   | `Farrell`              |
| **Phase**   | Phase 1                |
| **Stream**  | WS2 — Client Application |

---

## Scope — Owned Files

- `client/src/components/overlays/OverlayCanvas.tsx`
- `client/src/components/overlays/DiagnosticCard.tsx`
- `client/src/components/overlays/HazardWarning.tsx`
- `client/src/components/overlays/InfoBox.tsx`
- `client/src/components/overlays/MaskOverlay.tsx`
- `client/src/hooks/useOverlay.ts`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `OverlayCanvas.tsx`: transparent `<canvas>` absolutely positioned over video, z-index above camera
- `DiagnosticCard.tsx`: blue glow, fault identification, action button. Glassmorphic dark theme.
- `HazardWarning.tsx`: red pulsing, hazard label, severity level
- `InfoBox.tsx`: neutral glow, general information display
- `MaskOverlay.tsx`: SAM2 pixel-accurate mask rendered to canvas — semi-transparent fill + contour border (Phase 4+)
- `useOverlay.ts`: overlay state management, 8-second auto-dismiss timer, enter/exit animation triggers, multi-overlay support

---

## Verification

- [ ] Given a mock overlay response, the correct component renders at the correct pixel position
- [ ] Each overlay type renders with its correct visual style (blue/red/neutral glow)
- [ ] Overlay auto-dismisses after 8 seconds
- [ ] Multiple overlays render simultaneously without collision
- [ ] MaskOverlay renders RLE-decoded mask data onto canvas (test with fixture mask)
- [ ] Unit test: `useOverlay` hook manages add/remove/timeout lifecycle correctly
