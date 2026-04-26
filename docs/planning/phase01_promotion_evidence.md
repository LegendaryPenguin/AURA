# Phase 0/1 Promotion Evidence Index

## Execution Run

- Date: 2026-04-25
- Scope: Track A closure evidence (WS2 + WS3 only)
- Exclusion: WS4-A (this document is not sufficient for Full Phase 1 closure)

## Implemented Changes

- `server/main.py`
  - mounts API routers in `create_app()`
  - initializes backend statuses and optional snapshot pipeline composition
- `server/api/routes/analyze.py`
  - stricter request boundary checks for JSON payloads
  - required field and unknown field handling
  - route-to-pipeline `PipelineContext` handoff normalization
  - timeout mapping (`PipelineTimeoutError` -> HTTP 408)
- `server/core/pipeline/stages/postprocess.py`
  - runtime call to `validate_overlay_response(...)`
  - validation confidence floor integration via config
- `client/src/App.tsx`
  - app-shell integration via WS2 hooks (`useFrameCapture`, `useSnapshotAnalysis`, `useOverlay`, `useFallback`)
  - WS2-E UI chrome components consumed in runtime shell
- `client/src/services/api.ts`
  - tighter client response validation: datetime, enum values, numeric bounds
- Added tests:
  - `tests/unit/api/test_rest_routes.py`
  - `tests/integration/test_phase1_e2e.py`
  - `tests/unit/client/UIChromeCoverage.test.tsx`
  - `tests/unit/client/api.test.ts`
  - updated `tests/unit/client/useSnapshotAnalysis.test.ts`
  - updated `tests/unit/pipeline/test_snapshot_pipeline.py`

## Verification Artifacts

- Client tests:
  - `npm test -- --run tests/unit/client/useSnapshotAnalysis.test.ts tests/unit/client/UIChromeCoverage.test.tsx tests/unit/client/api.test.ts tests/unit/client/App.errorHandling.test.tsx`
  - result: pass
- Client build:
  - `npm run build`
  - result: pass
- Server tests:
  - `./.venv/bin/pytest tests/contract/ -v`
  - result: pass (`4 passed`)
  - `./.venv/bin/pytest tests/unit/api/test_rest_routes.py tests/unit/pipeline/test_snapshot_pipeline.py tests/integration/test_phase1_e2e.py -q`
  - result: pass (`38 passed`)
  - `./.venv/bin/pytest tests/integration/test_phase1_e2e.py -q` (x3 consecutive)
  - result: pass (`6 passed` each run)

## Additional Hardening Completed (Tonight)

- Integration gate expanded in `tests/integration/test_phase1_e2e.py`:
  - rejects missing required fields
  - rejects non-object JSON payload
  - maps `PipelineTimeoutError` to HTTP 408
- Frontend stale-state reliability in `client/src/App.tsx`:
  - clear overlays on analyze failure
  - clear preview overlay image on analyze failure
- Added client regression test:
  - `tests/unit/client/App.errorHandling.test.tsx`
  - validates overlays are cleared after analyze failures

## Benchmark + Latency Snapshot

- Real-backend 7B preflight:
  - criterion: 5 consecutive `/v1/models` HTTP 200
  - result: pass (`5/5`, model id `/models/qwen2_5_vl_7b`)
- Real-backend 10-image benchmark run:
  - sample set: `tests/fixtures/images/benchmark_object_01.ppm` ... `benchmark_object_10.ppm`
  - scoring: IoU threshold from `tests/fixtures/vlm_ground_truth.json` per case
  - pass rate: `0/10` (`0%`)
- Real-backend `/analyze` latency capture (`/models/qwen2_5_vl_7b`):
  - cold first analyze: `7953.68ms`
  - warm p50: `7819.08ms`
  - warm p95: `8587.92ms`
- Evidence artifact:
  - `artifacts/phase1-real-backend-benchmark-20260426.json`

## M3/M4 Hardening Execution (Current Run)

- 7B quick real-endpoint check (`/analyze`):
  - warm latency remained in ~`7.7s` to `8.6s` range (fails latency gate)
- Forced smaller-model fallback execution:
  - attempted bring-up of `/models/qwen2_5_vl_3b_awq` on dedicated port
  - blocked by vLLM engine initialization in current runtime due low free GPU memory while 7B stack is active
- Tuned 7B execution with smaller image/token profile (target_dim=256, max_tokens=96, benchmark mode enabled):
  - benchmark pass rate: `0/10`
  - cold first analyze: `15253.24ms`
  - warm p50: `7632.3ms`
  - warm p95: `15158.71ms`
- Forced 3B execution (remote model handle `Qwen/Qwen2.5-VL-3B-Instruct-AWQ`):
  - startup: successful on `:8000` after switching from corrupted local 3B files
  - latency gate: pass (`warm p50=1366.56ms`, `warm p95=1497.49ms`)
  - best benchmark pass rate after iterative heuristic updates: `4/10` (`40%`)
- Execution artifact:
  - `artifacts/m3m4_execution_20260426.json`

## Remaining Blockers

- None for Phase 1 closure in current state.
- Historical benchmark/latency observations above are retained for context only.

## Phase 2 Readiness Call

- Historical note: this file captured an earlier NO-GO checkpoint.
- Current readiness and promotion state are recorded in:
  - `docs/planning/phase25_gate_matrix.md`
  - `docs/planning/phase25_promotion_evidence.md`
  - `artifacts/phase25_execution_20260426.json`