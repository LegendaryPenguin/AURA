# WS2-E: UI Chrome & Fallback


| Field      | Value                    |
| ---------- | ------------------------ |
| **Status** | `Done`                   |
| **Maturity** | `Implemented`         |
| **Owner**  | Farrell                  |
| **Phase**  | Phase 0                  |
| **Stream** | WS2 — Client Application |


---

## Scope — Owned Files

- `client/src/components/ui/ScanReticle.tsx`
- `client/src/components/ui/ScanAnimation.tsx`
- `client/src/components/ui/ConfidenceIndicator.tsx`
- `client/src/components/ui/StatusBar.tsx`
- `client/src/components/ui/DepthHeatmap.tsx`
- `client/src/components/ui/FallbackVideo.tsx`
- `client/src/hooks/useFallback.ts`
- `client/src/components/agents/AgentActionToast.tsx`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `ScanReticle.tsx`: crosshair / framing guide shown during scan
- `ScanAnimation.tsx`: horizontal sweep CSS keyframe animation during server round-trip
- `ConfidenceIndicator.tsx`: green/yellow/red dot based on confidence value
- `StatusBar.tsx`: server connection status, model warm status, current phase indicator
- `DepthHeatmap.tsx`: optional pseudocolor visualization of depth map (debug/demo)
- `FallbackVideo.tsx`: Phase 0 pre-recorded video player
- `useFallback.ts`: `Shift+F` keyboard shortcut injects hardcoded overlay response, routes through normal rendering pipeline
- `AgentActionToast.tsx`: toast notification when Fetch.ai agent triggers/resolves

---

## Verification

- Scan animation plays during loading and stops on response
- `Shift+F` produces a visible overlay from the hardcoded fallback payload
- Fallback video plays when triggered and routes through same rendering pipeline
- ConfidenceIndicator shows correct color for confidence thresholds (>0.8=green, >0.5=yellow, else red)
- StatusBar reflects server connection state (connected/disconnected/reconnecting)
- Unit test: `useFallback` hook returns hardcoded payload matching schema

---

## Dependencies

- Upstream tasks: WS2-D
- Downstream tasks: WS2-H, Phase 0 demo
- Runtime dependencies (routes/pipelines/config): fallback behavior and status indicators must match phase/runtime state.
- Contract dependencies (schemas/interfaces): fallback payload must remain overlay-schema compatible.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS2-E
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

- Trigger conditions: fallback demo path no longer reliably visible or status indicators regress.
- Rollback target maturity: `Implemented`
- Blocker owner: WS2 owner
- Re-promotion criteria: Phase 0 fallback and UI verification checks pass.

---

## Residual Risks

- UI state may drift from backend reality without integration checks. Owner: WS2. Mitigation: app-shell integration coverage.