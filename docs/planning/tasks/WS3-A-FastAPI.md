# WS3-A: FastAPI Scaffold & Middleware


| Field      | Value                       |
| ---------- | --------------------------- |
| **Status** | `Todo`                      |
| **Owner**  | Farrell                     |
| **Phase**  | Phase 1                     |
| **Stream** | WS3 — Server API & Pipeline |


---

## Scope — Owned Files

- `server/main.py`
- `server/api/__init__.py`
- `server/api/middleware/cors.py`
- `server/api/middleware/error_handler.py`
- `server/api/middleware/__init__.py`
- `tests/unit/api/test_fastapi_scaffold.py`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `main.py`: FastAPI app factory. Register CORS, error handler middleware. Mount `api_router` from `server.api.routes`. Lifespan hook loads VLM backend (via `importlib`, no concrete class import — composition root pattern), builds snapshot pipeline via `build_snapshot_pipeline()`, and attaches both to `app.state.snapshot_pipeline` and `app.state.backend_statuses`. Startup event logs loaded backends.
- `cors.py`: configure allowed origins from `config/server.yaml`
- `error_handler.py`: catch all unhandled exceptions, return structured JSON: `{ "error": str, "code": int, "stage": str }`

---

## Verification

- Server starts and responds to `GET /` with 404 (no root route)
- CORS headers present on responses from configured origins
- Unhandled exception returns structured JSON error, not stack trace
- Server starts with zero model dependencies (all backends optional at startup)
- Unit test: error handler middleware catches and formats exceptions correctly
- Routes mounted: `GET /health` and `POST /analyze` are reachable
- Integration touchpoint: `app.state.snapshot_pipeline` is set (or None with fallback) before first request