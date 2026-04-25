# WS1-D: Scripts & Mock Server

| Field       | Value                      |
| ----------- | -------------------------- |
| **Status**  | `Todo`                     |
| **Owner**   | _Unassigned_               |
| **Sprint**  | Sprint 0 (Foundation)      |
| **Stream**  | WS1 — Foundation & Contracts |

---

## Scope — Owned Files

- `scripts/setup/install_server_deps.sh`
- `scripts/setup/install_client_deps.sh`
- `scripts/setup/setup_ssl.sh`
- `scripts/setup/download_models.sh`
- `scripts/startup/start_vllm.sh`
- `scripts/startup/start_sam2_service.sh`
- `scripts/startup/start_server.sh`
- `scripts/startup/warmup_all.sh`
- `scripts/dev/run_mock_server.sh`
- `scripts/dev/run_tests.sh`

> **Collision rule:** You may ONLY create or modify the files listed above. If you need functionality from another file, import — never edit.

---

## Work

- `install_server_deps.sh`: pip install from `requirements.txt`
- `install_client_deps.sh`: npm install in `client/`
- `setup_ssl.sh`: mkcert install, cert generation for local IP
- `download_models.sh`: pull Qwen2.5-VL-7B, SAM2, Depth Anything v2 weights
- `start_vllm.sh`: vLLM server for Qwen on port 8000
- `start_sam2_service.sh`: SAM2 ready
- `start_server.sh`: FastAPI on port 8443 with SSL
- `warmup_all.sh`: call /health until all models report ready
- `run_mock_server.sh`: FastAPI app returning canned schema-valid responses on all endpoints — no model loading. Supports `/analyze` (POST), `/stream` (WebSocket), `/health` (GET). Responses drawn from `tests/fixtures/responses/`.
- `run_tests.sh`: run all test suites (pytest + vitest + contract)

---

## Verification

- [ ] Mock server starts, `/health` returns 200
- [ ] Mock `/analyze` returns a schema-valid overlay response for any valid request
- [ ] Mock `/stream` accepts a WebSocket connection and returns overlay frames
- [ ] All scripts are executable and have correct shebangs
