# WS3-B: REST Routes

| Field       | Value                         |
| ----------- | ----------------------------- |
| **Status**  | `Done`                        |
| **Maturity**| `Verified`                    |
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

- `analyze.py`: `POST /analyze` — accept multipart or JSON body with canonical `image_base64` and optional `audio_base64` + `query`. Delegate to snapshot pipeline. Return overlay response or error.
- `health.py`: `GET /health` — return per-model readiness: `{vlm: "ready"|"loading"|"error", sam2: "ready"...}`. Aggregate status as `"healthy"` only if all required models are ready.
- `rate_limit.py`: if an `/analyze` request arrives while one is already processing, return HTTP 429 immediately. Never queue. Use `asyncio.Lock`.

---

## Verification

- [x] `POST /analyze` with valid fixture image returns 200 with schema-valid response (using mock pipeline)
- [x] `POST /analyze` with invalid image returns 422 with structured error
- [x] `GET /health` returns per-model status JSON
- [x] Concurrent `POST /analyze` requests: first gets 200, second gets 429
- [x] Unit test: rate limiter correctly blocks concurrent requests and releases after completion

---

## Current Execution Note (2026-04-25)

- Status for this pass: `DoNotPromote`
- Evidence index: `docs/planning/phase01_promotion_evidence.md`
- Changes landed: stricter JSON boundary checks in `/analyze` plus new route tests.
- Remaining gap: run server verification gates in a Python environment with project deps.
