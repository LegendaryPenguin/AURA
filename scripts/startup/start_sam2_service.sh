#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi
HOST="${SAM2_HOST:-0.0.0.0}"
PORT="${SAM2_PORT:-8001}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

echo "Starting lightweight SAM2 readiness service on ${HOST}:${PORT}"

exec "${PYTHON_BIN}" - <<'PY'
import os
from fastapi import FastAPI
import uvicorn

host = os.getenv("SAM2_HOST", "0.0.0.0")
port = int(os.getenv("SAM2_PORT", "8001"))

app = FastAPI(title="AURA SAM2 Service")

@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": "sam2", "ready": True}

@app.get("/ready")
def ready() -> dict[str, object]:
    return {"ready": True}

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port, log_level="info")
PY
