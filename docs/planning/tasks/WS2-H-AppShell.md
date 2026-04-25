# WS2-H: App Shell & Integration


| Field      | Value                    |
| ---------- | ------------------------ |
| **Status** | `Done`                   |
| **Maturity** | `Implemented`         |
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

---

## Dependencies

- Upstream tasks: WS2-C, WS2-D, WS2-F
- Downstream tasks: Phase-level integrations
- Runtime dependencies (routes/pipelines/config): app shell must accurately represent active phase and network/runtime readiness.
- Contract dependencies (schemas/interfaces): uses shared overlay/request typing through WS2-F path.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS2-H
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

- Trigger conditions: app shell bypasses dependency hooks or phase UX regresses.
- Rollback target maturity: `Implemented`
- Blocker owner: WS2 owner
- Re-promotion criteria: app-shell integration and manual verification checks pass.

---

## Residual Risks

- Manual PWA/mobile checks can lag automation. Owner: WS2. Mitigation: explicit pending manual gate tracking.

---

## Agent Handoff Note

- Current state (2026-04-25): WS2-H remains `Status: Done`, `Maturity: Implemented`.
- Automated gates executed and passing in local repo venv:
  - `pytest tests/contract/ -v`
  - `npm test -- --run` (from `client/`)
  - `pytest tests/integration/test_phase1_e2e.py -v`
- Promotion guidance for next agent:
  - `Implemented -> Integrated` is supported by current automated evidence.
  - Do not promote to `Verified` until manual mobile PWA install/fullscreen verification is completed and captured as evidence.
- Merge-safety note: no WS2-H code changes were made in this pass; this is documentation-only handoff context.