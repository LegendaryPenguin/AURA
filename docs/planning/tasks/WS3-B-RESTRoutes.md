# WS3-B: REST Routes

| Field       | Value                         |
| ----------- | ----------------------------- |
| **Status**  | `Done`                        |
| **Maturity** | `Implemented`               |
| **Owner**   | `Farrell`                     |
| **Phase**   | Phase 1                       |
| **Stream**  | WS3 — Server API & Pipeline   |

---

## Scope — Owned Files

- `server/api/routes/__init__.py`
- `server/api/routes/analyze.py`
- `server/api/routes/health.py`
- `server/api/middleware/rate_limit.py`
- `tests/unit/api/test_rest_routes.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `analyze.py`: `POST /analyze` — accept multipart or JSON body with `image_base64` and optional `audio_base64` + `query` (matching `shared/schemas/analysis_request.json`). Accept `image_b64`/`audio_b64` as fallback aliases. Delegate to snapshot pipeline. Return overlay response or error.
- `health.py`: `GET /health` — return per-model readiness: `{vlm: "ready"|"loading"|"error", sam2: "ready"...}`. Aggregate status as `"healthy"` only if all required models are ready.
- `rate_limit.py`: if an `/analyze` request arrives while one is already processing, return HTTP 429 immediately. Never queue. Use `asyncio.Lock`.

---

## Verification

- [x] `POST /analyze` with valid fixture image returns 200 with schema-valid response (using mock pipeline)
- [x] `POST /analyze` with invalid image returns 422 with structured error
- [x] `GET /health` returns per-model status JSON
- [x] Concurrent `POST /analyze` requests: first gets 200, second gets 429
- [x] Unit test: rate limiter correctly blocks concurrent requests and releases after completion
- [x] Integration touchpoint: confirm `_extract_request_payload` output keys match `shared/schemas/analysis_request.json` field names

---

## Dependencies

- Upstream tasks: WS1-A, WS3-A, WS3-D
- Downstream tasks: WS2-F, Phase 1 integration gate
- Runtime dependencies (routes/pipelines/config): `/analyze` and `/health` route behavior, rate limit controls.
- Contract dependencies (schemas/interfaces): request/response schema conformance and `PipelineContext` field contract.

---

## Promotion Evidence

Use this block before promotion beyond `Implemented`:

```
PromotionRecord:
  TaskID: WS3-B
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

- Trigger conditions: route contract mismatch, pipeline handoff failure, or rate-limit regressions.
- Rollback target maturity: `Implemented`
- Blocker owner: WS3 owner
- Re-promotion criteria: route unit/integration and contract gates pass.

---

## Residual Risks

- Alias handling may mask contract drift if not explicitly tracked. Owner: WS3. Mitigation: route-boundary contract tests.
