# WS2-H Samsung Internet Installability Plan

## Objective

Close the WS2-H manual install/fullscreen blocker by making Samsung Internet behave consistently like an installed app and documenting successful evidence.

## Scope (Minimal, WS2-H-focused)

- `client/index.html`
- `client/src/main.tsx`
- `client/src/App.tsx` (only for minimal runtime diagnostics if needed)
- `client/vite.config.ts` (only if required for host/tunnel behavior)
- `client/public/manifest.webmanifest`
- `client/public/sw.js`
- `client/public/icons/*`
- `docs/planning/tasks/WS2-H-AppShell.md`
- `docs/planning/phase01_promotion_evidence.md`

Out of scope: WS4-A, server inference, major caching architecture changes.

## Problem Breakdown

1. Samsung Internet only shows “Add to Home” path (no ambient install badge).
2. Homescreen launch still feels browser-like (pull-to-refresh, camera black).
3. Rotating tunnel URL likely causes origin/permission/install identity churn.

## Implementation Plan

### 1) Stabilize Install Origin

- Choose a repeatable HTTPS origin for verification (same host each test run as much as possible).
- Keep tunnel/session stable during one verification cycle; do not reinstall across changing origins.

### 2) Manifest Compatibility Hardening

- Ensure manifest has:
  - `id`
  - `start_url` and `scope` alignment
  - `display: "standalone"`
  - valid PNG icon entries (192/512)
- Keep current branding/theme values.

### 3) Service Worker Control Validation

- Confirm:
  - SW registers successfully,
  - SW activates,
  - page is controlled on installed launch.
- If camera black correlates with first-load control race, add minimal reload/control guard logic only if necessary.

### 4) Minimal App-Feel Tuning

- Add conservative UX tuning to reduce browser feel:
  - prevent overscroll pull-to-refresh behavior where appropriate.
- Add temporary diagnostics for install context (standalone display mode + camera permission status) if needed to pinpoint Samsung behavior.

### 5) Manual Verification Matrix

Run both:

- Samsung Internet (primary target)
- Chrome Android (control comparison)

Check:

- install path visible (prompt or menu),
- homescreen launch opens standalone/fullscreen,
- camera usable after installed launch,
- app shell responsive (phase switch/analyze path).

## Evidence Requirements

Record in `docs/planning/phase01_promotion_evidence.md`:

- device + OS + browser version,
- URL origin used,
- install method (badge/menu),
- standalone/fullscreen result,
- camera result,
- screenshot references.

Update `docs/planning/tasks/WS2-H-AppShell.md`:

- manual PWA verification checkbox,
- WS2-H promotion note with evidence links.

## Done Criteria

- Samsung Internet install flow succeeds (menu path acceptable).
- Installed launch behaves standalone/fullscreen enough for WS2-H acceptance.
- Camera no longer black in installed context for verified origin.
- WS2-H manual evidence documented and ready for promotion decision.