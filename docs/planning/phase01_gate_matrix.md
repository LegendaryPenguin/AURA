# Phase 0/1 Gate Matrix

## Purpose

Track closure readiness for required Phase 0 and Phase 1 tasks without touching WS4-A.

## Status Snapshot (Current Pass)


| Task  | Required Maturity | Current Maturity | Outcome      | Blocking Reason                                           |
| ----- | ----------------- | ---------------- | ------------ | --------------------------------------------------------- |
| WS2-E | Verified          | Implemented      | DoNotPromote | Promotion record and end-to-end evidence still incomplete |
| WS2-H | Integrated        | Implemented      | DoNotPromote | Manual PWA/mobile verification evidence pending           |
| WS2-C | Verified          | Implemented      | DoNotPromote | Mapper-runtime closure evidence not finalized             |
| WS2-D | Verified          | Implemented      | DoNotPromote | Promotion artifacts/signoff pending                       |
| WS2-F | Verified          | Implemented      | DoNotPromote | Needs full gate artifact package and signoff              |
| WS3-A | Verified          | Implemented      | DoNotPromote | Python test env unresolved locally                        |
| WS3-B | Verified          | Implemented      | DoNotPromote | Python test env unresolved locally                        |
| WS3-D | Verified          | Implemented      | DoNotPromote | Python test env unresolved locally                        |
| WS3-F | Verified          | Implemented      | DoNotPromote | Python test env unresolved locally                        |
| WS4-A | Verified          | User-skipped     | Excluded     | Explicitly excluded by user request                       |


## Required Next Steps

1. Activate server test environment (`fastapi`, `pydantic`, and test extras).
2. Run:
  - `pytest tests/contract/ -v`
  - `pytest tests/unit/api/test_rest_routes.py tests/unit/pipeline/test_snapshot_pipeline.py tests/integration/test_phase1_e2e.py -q`
3. Fill PromotionRecord sections and signoffs for required WS2/WS3 tasks.
4. Update roadmap phase claims only after all required gates pass.