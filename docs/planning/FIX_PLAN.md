# AURA Comprehensive Fix Plan

> **Produced:** 2026-04-26
> **Scope:** All issues preventing the application from functioning across Phases 0–3
> **Priority:** Issues are ranked P0 (app-breaking) → P1 (feature-breaking) → P2 (correctness) → P3 (hardening)

---

## Executive Summary

The AURA app has **no failing tests** (103 Python / 34 client all green), yet the application **does not work in the browser**. The root causes fall into three categories:

1. **React render-loop cascade** — unstable callback references propagate through `useSnapshotAnalysis` → `runAnalyze` → `useAutoScan`, causing infinite effect re-subscriptions, interval resets, and stacked scans in Phase 3.
2. **Port/protocol mismatch** — the Vite dev proxy targets `http://localhost:8080` while the server scripts launch on `https://localhost:8443`, so no requests ever reach the backend.
3. **Fallback bbox semantics wrong** — `useFallback` returns `[x_min, y_min, x_max, y_max]` tuples but `App.tsx` maps index 2/3 to `width`/`height`, producing wrong rectangles in Phase 0.

These three issues account for **all phases appearing broken**. Below is the full catalogue plus 12 additional correctness/hardening issues discovered during audit.

---

## Issue Catalogue

### Category A — React Render-Loop Chain (P0)

These four issues form a single chain. Fixing any one breaks the cycle, but all four should be fixed for correctness.

| ID | File | Lines | Issue | Impact |
|----|------|-------|-------|--------|
| A1 | `client/src/hooks/useSnapshotAnalysis.ts` | 124 | `useCallback(..., [dependencies])` — `dependencies` is a new object literal every render from App, so `runAnalysis` recreates every render. | `snapshot` object is never stable → everything downstream churns. |
| A2 | `client/src/App.tsx` | 65–68 | `recordAudioForApi` depends on `audio` (the whole return object from `useAudioRecorder`), which is a new reference every render. | `recordAudioForApi` changes every render → feeds into A1. |
| A3 | `client/src/App.tsx` | 131–155 | `runAnalyze` depends on `snapshot` (whole object from `useSnapshotAnalysis`), which changes every render due to A1. | `runAnalyze` identity changes every render. |
| A4 | `client/src/hooks/useAutoScan.ts` | 33–48, 60–70 | `runScan` depends on `onScan` (which is `runAnalyze` from A3). When `onScan` changes, the interval effect re-runs: clears timer, starts new interval, **and fires `void runScan()` immediately**. | Phase 3 auto-scan: constant interval resets + immediate re-scans on every parent render. |

### Category B — Network / Configuration (P0)

| ID | File | Lines | Issue | Impact |
|----|------|-------|-------|--------|
| B1 | `client/vite.config.ts` | 9, 13, 17 | Proxy targets `http://localhost:8080`. Server scripts start on `https://localhost:8443`. **No service listens on 8080.** | All API calls from the browser fail (connection refused). Health check fails → "disconnected" forever. |
| B2 | `config/server.yaml` | 27–29 | CORS allows only `https://localhost:5173`. Default Vite dev is `http://localhost:5173`. If browser ever bypasses proxy, CORS blocks the request. | Direct API calls blocked by CORS (proxy avoids this, but fallback is broken). |
| B3 | `config/server.yaml` vs `start_server.sh` | — | SSL cert paths in YAML (`./certs/`) don't match `start_server.sh` defaults (`config/ssl/`). `.env.example` var names (`AURA_SERVER_PORT`) don't match script names (`AURA_PORT`). | Confusing for operators; starting the server with YAML-documented paths would fail. |

### Category C — Fallback / Overlay Data (P1)

| ID | File | Lines | Issue | Impact |
|----|------|-------|-------|--------|
| C1 | `client/src/App.tsx` | 98–106 | Maps `fallbackData.overlays[].bbox` as `{ x: bbox[0], y: bbox[1], width: bbox[2], height: bbox[3] }`. But `useFallback` returns `[x_min, y_min, x_max, y_max]`, not `[x, y, w, h]`. | Phase 0: overlay rectangles are wrong (width = x_max value like 0.55 instead of 0.43). |
| C2 | `client/src/hooks/useFallback.ts` | 5–6, 22–51 | `OverlayItem.bbox` typed as `[number, number, number, number]` and `ui_layer` as `number` — separate types from the shared schema's `OverlayItem` which uses `{ x, y, width, height }` and string `ui_layer`. | Type confusion between fallback and real overlay data; requires mapping code in App that is currently wrong (C1). |
| C3 | `client/src/components/overlays/OverlayCanvas.tsx` | 92–136 | Canvas `useEffect` depends only on `sortedOverlays`; no resize listener. If window resizes, `getBoundingClientRect()` is stale until next overlay update. | Overlays misaligned after window resize until next data update. |

### Category D — Server Pipeline (P1)

| ID | File | Lines | Issue | Impact |
|----|------|-------|-------|--------|
| D1 | `server/api/routes/analyze.py` | 91–100 | `_run_snapshot_pipeline` is `async def` but runs the synchronous `pipeline.run()` in the event loop without `asyncio.to_thread()`. | Blocks the entire FastAPI event loop during inference (seconds). Health checks and other requests stall. |
| D2 | `server/core/pipeline/stages/transcribe.py` | 25–27, 41–46 | When Whisper is not loaded, falls back to `self._backend.transcribe()` (VLM), which raises `NotImplementedError`. The `except` silently swallows it and uses default query. | Audio is silently ignored when Whisper isn't available — users think voice worked but it didn't. |
| D3 | `server/api/middleware/rate_limit.py` | 19–29 | `_load_rate_limit_config()` re-reads and parses `config/server.yaml` on **every** request. | Unnecessary filesystem I/O per request; slight latency + potential race on config changes. |

### Category E — Hook Return Stability (P2)

These aren't direct render-loop causes in the *current* App.tsx (because eslint-disabled deps avoid the worst chains), but they are latent bugs that would surface if any consumer puts the hook return in a dependency array.

| ID | File | Lines | Issue |
|----|------|-------|-------|
| E1 | `client/src/hooks/useAudioRecorder.ts` | 99 | Returns a new object every render (not memoized). |
| E2 | `client/src/hooks/useCamera.ts` | 95 | Returns a new object every render (not memoized). |
| E3 | `client/src/hooks/useAutoScan.ts` | 72 | Returns a new object every render (not memoized). |
| E4 | `client/src/hooks/useFrameCapture.ts` | 59 | Returns a new object every render (not memoized). |
| E5 | `client/src/hooks/useFallback.ts` | 89 | Returns a new object every render (not memoized). |

### Category F — Hardening / Edge Cases (P3)

| ID | File | Lines | Issue |
|----|------|-------|-------|
| F1 | `client/src/services/api.ts` | 3, 123–150 | 5-second client timeout (`REQUEST_TIMEOUT_MS`) may fire during normal inference (VLM can take 3–10s). |
| F2 | `client/src/services/api.ts` | 152–156 | JSON parse errors on successful responses classified as `NETWORK_ERROR`. |
| F3 | `client/src/types/overlay.ts` | 15–20 | `HealthResponse` type has `model_status`, `version`, `details` — server returns `status`, `models`. |
| F4 | `server/core/inference/vlm/qwen_vl.py` | 154–160 | Greedy regex for JSON extraction can match wrong bracket span on nested JSON. |
| F5 | `server/core/inference/audio/whisper_backend.py` | 59 | Hard-coded `.webm` temp file suffix; non-WebM audio may fail unpredictably. |
| F6 | `server/core/inference/audio/whisper_backend.py` | 23–24 | `max_duration_seconds` parameter is never enforced. |
| F7 | `client/vite.config.ts` | 20–24 | `/ws` proxy endpoint configured but no WebSocket route exists on the server. |
| F8 | `config/models.yaml` | vlm section | `vlm.model_id` and `vlm.endpoint` are not wired into `QwenVLBackend` from `main.py` — env vars win; YAML is documentation-only. |

---

## Fix Plan

### Fix 1: Break the Render-Loop Chain (A1–A4)

**Files:** `useSnapshotAnalysis.ts`, `App.tsx`, `useAutoScan.ts`

**Strategy:** Use `useRef` to hold the latest unstable callback, and pass a stable wrapper to dependency arrays.

#### Fix 1a: `useSnapshotAnalysis.ts` — Stabilize `runAnalysis`

```typescript
// Replace [dependencies] in useCallback with destructured stable refs
const captureFrameRef = useRef(dependencies.captureFrame);
const recordAudioRef = useRef(dependencies.recordAudio);

useEffect(() => { captureFrameRef.current = dependencies.captureFrame; }, [dependencies.captureFrame]);
useEffect(() => { recordAudioRef.current = dependencies.recordAudio; }, [dependencies.recordAudio]);

const runAnalysis = useCallback(async (input) => {
  // ... use captureFrameRef.current() and recordAudioRef.current() instead of dependencies.*
}, []); // Now stable — no deps
```

#### Fix 1b: `App.tsx` — Stabilize `recordAudioForApi`

```typescript
// Depend on audio.stopRecording (stable useCallback) instead of the whole `audio` object
const recordAudioForApi = useCallback(async () => {
  if (phaseMode < 2) return undefined;
  return audio.stopRecording();
}, [phaseMode, audio.stopRecording]);
```

#### Fix 1c: `App.tsx` — Stabilize `runAnalyze`

```typescript
// Use snapshot.runAnalysis (now stable from 1a) instead of the whole `snapshot` object
const runAnalyze = useCallback(async () => {
  if (phaseMode === 0) return;
  setError(null);
  try {
    const response = await snapshot.runAnalysis({ ... });
    hydrateFromResponse(response);
  } catch (e) { ... }
}, [phaseMode, camera.videoRef, snapshot.runAnalysis, hydrateFromResponse]);
```

#### Fix 1d: `useAutoScan.ts` — Stabilize `onScan` with ref

```typescript
const onScanRef = useRef(onScan);
useEffect(() => { onScanRef.current = onScan; }, [onScan]);

const runScan = useCallback(async () => {
  if (scanningRef.current) return;
  scanningRef.current = true;
  setLastError(null);
  try {
    await onScanRef.current(); // Use ref, not direct dep
    setScanCount(c => c + 1);
    setLastScanTs(Date.now());
  } catch (err) { ... }
  finally { scanningRef.current = false; }
}, []); // Stable — no deps

// Effect now only depends on [isAutoScanning, enabled, intervalMs, clearTimer]
// runScan is stable, so interval is not reset on parent re-render
```

**Verification:** After applying, run `npm run dev`, open browser console, confirm:
- No "Maximum update depth exceeded" error
- Phase 3 auto-scan fires at the configured interval (2.5s), not continuously
- Phase 1/2 manual capture works without console warnings

---

### Fix 2: Correct Port/Protocol Configuration (B1–B3)

**Files:** `client/vite.config.ts`, `config/server.yaml`

#### Fix 2a: `vite.config.ts` — Match the actual server

```typescript
proxy: {
  "/analyze": { target: "https://localhost:8443", changeOrigin: true, secure: false },
  "/health":  { target: "https://localhost:8443", changeOrigin: true, secure: false },
  "/api":     { target: "https://localhost:8443", changeOrigin: true, secure: false },
}
```

`secure: false` is needed because the dev server uses a self-signed cert.

#### Fix 2b: `config/server.yaml` — Add HTTP origins

```yaml
cors:
  allowed_origins:
    - "https://localhost:5173"
    - "https://127.0.0.1:5173"
    - "http://localhost:5173"     # <-- ADD
    - "http://127.0.0.1:5173"    # <-- ADD
```

#### Fix 2c: Align config documentation

- Update `config/server.yaml` SSL paths to match `scripts/startup/start_server.sh` defaults
- Update `.env.example` variable names to match script names (`AURA_PORT`, `AURA_HOST`, etc.)

**Verification:** Start server with `./scripts/startup/start_server.sh`, start client with `npm run dev`. Browser console should show "connected" status on health check.

---

### Fix 3: Correct Fallback BBox Mapping (C1–C2)

**File:** `client/src/App.tsx`

The fallback data uses `[x_min, y_min, x_max, y_max]` format. Convert to `{ x, y, width, height }`:

```typescript
const mapped = fallbackData.overlays.map((o, i) => ({
  id: `fallback-${i}`,
  bbox: {
    x: o.bbox[0],
    y: o.bbox[1],
    width: o.bbox[2] - o.bbox[0],   // x_max - x_min
    height: o.bbox[3] - o.bbox[1],  // y_max - y_min
  },
  label: o.label,
  confidence: o.confidence,
  ui_layer: LAYER_BY_INDEX[o.ui_layer] ?? "midground",
  overlay_type: TYPE_BY_NAME[o.overlay_type] ?? "info",
  action_required: o.action_required,
}));
```

**Verification:** Phase 0 should show correctly-sized overlay rectangles matching the demo content.

---

### Fix 4: Offload Pipeline to Thread (D1)

**File:** `server/api/routes/analyze.py`

Wrap the synchronous pipeline execution in `asyncio.to_thread`:

```python
async def _run_snapshot_pipeline(pipeline, payload):
    result = await asyncio.to_thread(pipeline.run, payload)
    return result.response
```

**Verification:** Start two browser tabs. Fire `/analyze` in one; `/health` in the other should respond immediately without waiting for inference to complete.

---

### Fix 5: Add Resize Observer to OverlayCanvas (C3)

**File:** `client/src/components/overlays/OverlayCanvas.tsx`

Add a `ResizeObserver` on the parent element so the canvas redraws when the container size changes:

```typescript
const [canvasSize, setCanvasSize] = useState({ w: 0, h: 0 });

useEffect(() => {
  const parent = canvasRef.current?.parentElement;
  if (!parent) return;
  const observer = new ResizeObserver(([entry]) => {
    const { width, height } = entry.contentRect;
    setCanvasSize({ w: width, h: height });
  });
  observer.observe(parent);
  return () => observer.disconnect();
}, []);

// Add canvasSize to the drawing useEffect's dependency array
```

---

### Fix 6: Memoize Hook Returns (E1–E5)

For each hook, wrap the return value in `useMemo`:

**`useAudioRecorder.ts`:**
```typescript
return useMemo(() => ({
  isRecording, startRecording, stopRecording, holdToRecord, error
}), [isRecording, startRecording, stopRecording, holdToRecord, error]);
```

Apply the same pattern to `useCamera`, `useAutoScan`, `useFrameCapture`, and `useFallback`.

---

### Fix 7: Improve Whisper Fallback UX (D2)

**File:** `server/core/pipeline/stages/transcribe.py`

When Whisper is unavailable and audio was provided, log a warning and include it in the response so the user knows their voice wasn't processed:

```python
if audio_base64 and not self._whisper_backend:
    context.response.setdefault("warnings", []).append(
        "Audio was provided but Whisper is not available. Using default text query."
    )
```

---

### Fix 8: Cache Rate-Limit Config (D3)

**File:** `server/api/middleware/rate_limit.py`

Load config once at module import or in a cached function, not on every request:

```python
import functools

@functools.lru_cache(maxsize=1)
def _load_rate_limit_config():
    ...
```

---

### Fix 9: Increase Client Timeout (F1)

**File:** `client/src/services/api.ts`

Change `REQUEST_TIMEOUT_MS` from `5000` to `15000` to accommodate VLM inference time.

---

### Fix 10: Fix HealthResponse Type (F3)

**File:** `client/src/types/overlay.ts`

Align `HealthResponse` with what the server actually returns:

```typescript
export interface HealthResponse {
  status: string;
  models?: Record<string, unknown>;
}
```

---

## Execution Order

| Step | Fix | Priority | Est. LOC Changed | Dependencies |
|------|-----|----------|-------------------|--------------|
| 1 | Fix 1a (useSnapshotAnalysis ref pattern) | P0 | ~15 | None |
| 2 | Fix 1d (useAutoScan ref pattern) | P0 | ~10 | None |
| 3 | Fix 1b (recordAudioForApi deps) | P0 | ~2 | None |
| 4 | Fix 1c (runAnalyze deps) | P0 | ~3 | After 1a |
| 5 | Fix 2a (vite proxy port) | P0 | ~6 | None |
| 6 | Fix 2b (CORS origins) | P0 | ~2 | None |
| 7 | Fix 3 (fallback bbox) | P1 | ~4 | None |
| 8 | Fix 4 (pipeline thread) | P1 | ~3 | None |
| 9 | Fix 5 (resize observer) | P2 | ~15 | None |
| 10 | Fix 6 (memoize returns) | P2 | ~25 | None |
| 11 | Fix 7 (whisper UX) | P2 | ~5 | None |
| 12 | Fix 8 (cache config) | P3 | ~5 | None |
| 13 | Fix 9 (client timeout) | P3 | ~1 | None |
| 14 | Fix 10 (health type) | P3 | ~5 | None |
| 15 | Fix 2c (config alignment) | P3 | ~10 | None |

---

## Verification Checklist

After all fixes are applied:

- [ ] `python -m pytest tests/ -v` — all pass (103+)
- [ ] `npx vitest run` — all pass (34+)
- [ ] Phase 0: Demo video plays, overlay rectangles correctly positioned
- [ ] Phase 1: Camera starts, "Capture + Analyze" sends request to server, overlay appears
- [ ] Phase 2: Camera + audio recording, voice query reaches server
- [ ] Phase 3: Auto-scan fires at 2.5s intervals (not continuously), no console errors
- [ ] Browser console: zero "Maximum update depth exceeded" warnings
- [ ] Browser console: zero CORS errors
- [ ] Server: `/health` responds while `/analyze` is processing (not blocked)
- [ ] Window resize: overlay canvas redraws correctly

---

## Addendum: Additional Issues Found During Live Testing (2026-04-26 post-execution)

### Fix 2a (REVISED): Configurable Proxy Target

The original Fix 2a hard-coded `https://localhost:8443` but the dev server was running on `http://localhost:8080`.
The proxy target is now configurable via `VITE_API_TARGET` env var, defaulting to `http://localhost:8080`
to match the common dev setup. Set `VITE_API_TARGET=https://localhost:8443` for SSL mode.

### Fix 11: VLM JSON Parsing — "Extra data" error (P0)

**File:** `server/core/inference/vlm/qwen_vl.py`

The VLM sometimes returns valid JSON followed by extra text, causing `json.loads()` to fail with
"Extra data: line N column M". The regex fallback also had unguarded `json.loads()` calls.

**Fix:** Replaced the brittle regex-based fallback with `json.JSONDecoder().raw_decode()` which
correctly parses the first JSON token and ignores trailing content.

### Fix 12: Pipeline Timeouts Too Aggressive (P0)

**File:** `config/pipeline.yaml`

The original timeouts (analyze: 1200ms, total: 2000ms) were too tight for real VLM inference
which takes 1-3 seconds. Increased to analyze: 8000ms, total: 12000ms.

---

## Issues NOT Addressed (Out of Scope)

These are known but do not prevent the app from functioning:

1. **No true concurrent 429 test** — `TestClient` is synchronous; would need `httpx.AsyncClient`
2. **SAM2 in-process vs service confusion** — `warmup_all.sh` checks port 8001 but `main.py` loads SAM2 in-process
3. **Streaming/WebSocket** — `/ws` proxy configured but no server endpoint exists
4. **`models.yaml` VLM config not wired** — env vars control VLM backend, YAML is documentation-only
5. **Missing `start_client.sh`** — no startup script for the client dev server
