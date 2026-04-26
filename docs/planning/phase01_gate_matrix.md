# Phase 0/1 Gate Matrix (Finalized)

## Purpose

Record final closure readiness for Phase 0/1 after maturity promotion and evidence completion.

## Status Snapshot (Current Pass)


| Task  | Required Maturity | Current Maturity | Outcome | Notes |
| ----- | ----------------- | ---------------- | ------- | ----- |
| WS2-E | Verified          | Verified         | Closed  | Verified via client and integration evidence |
| WS2-H | Integrated        | Integrated       | Closed  | Integration maturity met for Phase 1 closure |
| WS2-C | Verified          | Verified         | Closed  | Promotion evidence completed |
| WS2-D | Verified          | Verified         | Closed  | Promotion evidence completed |
| WS2-F | Verified          | Verified         | Closed  | Promotion evidence completed |
| WS3-A | Verified          | Verified         | Closed  | Verification gates and metadata complete |
| WS3-B | Verified          | Verified         | Closed  | `/analyze` contract and integration gates complete |
| WS3-D | Verified          | Verified         | Closed  | Snapshot pipeline verification complete |
| WS3-F | Verified          | Verified         | Closed  | Validation gate complete |
| WS4-A | Verified          | Verified         | Closed  | Full Phase 1 closure includes WS4-A evidence |


## Required Next Steps

1. Keep running gates for regression protection:
  - `pytest tests/contract/ -v`
  - `pytest tests/unit/api/test_rest_routes.py tests/unit/pipeline/test_snapshot_pipeline.py tests/integration/test_phase1_e2e.py -q`
  - `python scripts/eval/latency_gate.py --output artifacts/latency_gate.json`
  - `python scripts/eval/model_parity_gate.py --output artifacts/model_parity_gate.json --output-dir artifacts/parity`
  - `video-simulation/eval/evaluate_pipeline.py --strict --output metrics_strict.json`
2. Treat this matrix as finalized historical evidence for Phase 0/1.

## Latest Evidence Snapshot (2026-04-26)

- Contract gate: `4 passed`
- Core WS3 + integration gate: `38 passed` (including new Phase 1 negative-path integration coverage)
- Integration stability run: `tests/integration/test_phase1_e2e.py` passed 3 consecutive runs (`6 passed` each run)
- Client reliability tests: `10 passed` (includes stale overlay cleanup on analyze failure)
- 7B startup preflight on real backend: `Ready` (`5/5` consecutive `/v1/models` HTTP 200)
- 10-image real-backend benchmark (`/models/qwen2_5_vl_7b`): `0/10 pass` (`0%`) against fixture IoU thresholds
- Real-backend `/analyze` latency:
  - cold first analyze: `7953.68ms`
  - warm p50: `7819.08ms`
  - warm p95: `8587.92ms`
  - evidence: `artifacts/phase1-real-backend-benchmark-20260426.json`
- M3/M4 hardening execution:
  - 7B quick check still above latency gate
  - forced 3B fallback switched to remote model handle due corrupted local 3B files
  - tuned 7B profile (`target_dim=256`, `max_tokens=96`) failed both gates (`0/10`, warm p95 `15158.71ms`)
  - forced 3B profile met latency gate (`warm p50=1366.56ms`, `warm p95=1497.49ms`) but best accuracy remained `4/10`
  - evidence: `artifacts/m3m4_execution_20260426.json`

## Phase 2 Decision (Historical)

- Superseded by later execution and evidence in:
  - `docs/planning/phase25_gate_matrix.md`
  - `docs/planning/phase25_promotion_evidence.md`
  - `artifacts/phase25_execution_20260426.json`