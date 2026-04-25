# WS2-E: UI Chrome & Fallback

| Field       | Value                  |
| ----------- | ---------------------- |
| **Status**  | `Todo`                 |
| **Owner**   | _Unassigned_           |
| **Phase**   | Phase 0                |
| **Stream**  | WS2 — Client Application |

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

- [ ] Scan animation plays during loading and stops on response
- [ ] `Shift+F` produces a visible overlay from the hardcoded fallback payload
- [ ] Fallback video plays when triggered and routes through same rendering pipeline
- [ ] ConfidenceIndicator shows correct color for confidence thresholds (>0.8=green, >0.5=yellow, else red)
- [ ] StatusBar reflects server connection state (connected/disconnected/reconnecting)
- [ ] Unit test: `useFallback` hook returns hardcoded payload matching schema
