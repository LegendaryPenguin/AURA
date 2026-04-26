# Phase 0/1 Promotion Evidence Index

## Execution Run

- Date: 2026-04-25
- Scope: WS2 + WS3 Phase 0/1 completion work
- Explicit exclusion: WS4-A

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
  - `npm test -- --run tests/unit/client/useSnapshotAnalysis.test.ts tests/unit/client/UIChromeCoverage.test.tsx tests/unit/client/api.test.ts`
  - result: pass
- Client build:
  - `npm run build`
  - result: pass
- Server tests:
  - pending in this environment (`fastapi` / `pydantic` not available locally)

## Remaining Blockers

- WS2-H manual PWA/mobile verification evidence remains pending.
- Python environment setup required for WS3 verification gates.
- WS4-A intentionally excluded (user request).