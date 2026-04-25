# WS2-H: App Shell & Integration

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Todo`                 |
| **Owner**   | _Unassigned_           |
| **Phase**   | Integration            |
| **Stream**  | WS2 — Client Application |

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

- `App.tsx`: top-level routing, phase mode selector (0–5), compose camera + overlays + UI chrome
- `main.tsx`: React root mount
- Vite config with HTTPS proxy for development, source maps
- PWA manifest for mobile home screen installation

---

## Verification

- [ ] App renders camera view with overlay canvas on top
- [ ] Phase mode selector switches between fallback/snapshot/streaming modes
- [ ] Build completes with zero TypeScript errors
- [ ] PWA installs on mobile and opens fullscreen
- [ ] Integration test: full flow against mock server — open camera → capture → send → render overlay
