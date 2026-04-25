# WS2-H: App Shell & Integration


| Field      | Value                    |
| ---------- | ------------------------ |
| **Status** | `Done`                   |
| **Owner**  | Farrell                  |
| **Phase**  | Integration              |
| **Stream** | WS2 — Client Application |
| **Depends** | WS2-C (useFrameCapture), WS2-D (useOverlay, OverlayCanvas), WS2-F (api.ts, useSnapshotAnalysis) |


---

## Scope — Owned Files

- `client/src/App.tsx`
- `client/src/main.tsx`
- `client/package.json`
- `client/vite.config.ts`
- `client/tsconfig.json`
- `client/index.html`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `App.tsx`: top-level routing, phase mode selector (0–5), compose camera + overlays + UI chrome. Must import and use `useFrameCapture`, `useSnapshotAnalysis`, `useOverlay`, and `OverlayCanvas` for Phase 1+ — do not use inline fetch or inline canvas drawing for analysis flow.
- `main.tsx`: React root mount
- Vite config with HTTPS proxy for development, source maps
- PWA manifest for mobile home screen installation

---

## Verification

- [x] App renders camera view with overlay canvas on top
- [x] Phase mode selector switches between fallback/snapshot/streaming modes
- [x] Build completes with zero TypeScript errors
- [ ] PWA installs on mobile and opens fullscreen *(manual mobile verification pending)*
- [x] API integration: `tests/integration/test_phase1_e2e.py` validates POST `/analyze` with `image_base64` (browser flow uses the same via `useSnapshotAnalysis` + `api.ts`)
- [x] Integration touchpoint: App.tsx imports and uses hooks from WS2-C/D/F, does not bypass them with inline fetch