# Phase 0/1 Gate Matrix

## Purpose

Track closure readiness for required Phase 0 and Phase 1 tasks without touching WS4-A.

## Status Snapshot (Current Pass)


| Task  | Required Maturity | Current Maturity | Outcome      | Blocking Reason                                           |
| ----- | ----------------- | ---------------- | ------------ | --------------------------------------------------------- |
| WS2-E | Verified          | Implemented      | DoNotPromote | Promotion record and signoff still pending                |
| WS2-H | Integrated        | Implemented      | DoNotPromote | Manual PWA/mobile verification evidence pending           |
| WS2-C | Verified          | Implemented      | DoNotPromote | Promotion signoff pending                                 |
| WS2-D | Verified          | Implemented      | DoNotPromote | Promotion signoff pending                                 |
| WS2-F | Verified          | Implemented      | DoNotPromote | Promotion signoff pending                                 |
| WS3-A | Verified          | Implemented      | ReadyForPromotion | Verification gates pass; promotion metadata pending   |
| WS3-B | Verified          | Implemented      | ReadyForPromotion | `/analyze` contract and integration gates pass       |
| WS3-D | Verified          | Implemented      | ReadyForPromotion | Snapshot pipeline unit/integration gates pass        |
| WS3-F | Verified          | Implemented      | ReadyForPromotion | Validation path exercised in integration gate        |
| WS4-A | Verified          | User-skipped     | Excluded     | Explicitly excluded by user request                       |


## Required Next Steps

1. Promote WS3-A/B/D/F from `Implemented` to `Verified` with owner signoff.
2. Complete WS2 promotion records/signoffs (WS2-E/H/C/D/F), including manual mobile/PWA evidence for WS2-H.
3. Keep running gates:
  - `pytest tests/contract/ -v`
  - `pytest tests/unit/api/test_rest_routes.py tests/unit/pipeline/test_snapshot_pipeline.py tests/integration/test_phase1_e2e.py -q`
4. Update roadmap phase claims only after all required WS2/WS3 maturity promotions are signed off.

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

## Phase 2 Decision (Current)

- **NO-GO (technical + formal):**
  - technical blocker: real-backend accuracy baseline failed (`0%` vs required `>=80%`) and latency is far above target
  - fallback blocker: forced 3B is active and fast enough, but accuracy gate still fails (`4/10` best vs required 10/10)
  - formal blockers: required WS2 promotion signoffs and WS2-H manual verification evidence are still incomplete
- **Next action:** keep Phase 1 in hardening mode; do not start Phase 2 until real-backend accuracy and latency gates are met.