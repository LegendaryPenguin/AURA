#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi
HOST="${MOCK_HOST:-0.0.0.0}"
PORT="${MOCK_PORT:-8443}"
RESPONSES_DIR="${MOCK_RESPONSES_DIR:-${ROOT_DIR}/tests/fixtures/responses}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ ! -d "${RESPONSES_DIR}" ]]; then
  echo "Mock responses directory does not exist: ${RESPONSES_DIR}" >&2
  exit 1
fi

echo "Starting AURA mock server on ${HOST}:${PORT}"
echo "Loading responses from ${RESPONSES_DIR}"

export MOCK_HOST="${HOST}"
export MOCK_PORT="${PORT}"
export MOCK_RESPONSES_DIR="${RESPONSES_DIR}"

exec "${PYTHON_BIN}" - <<'PY'
import itertools
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

host = os.getenv("MOCK_HOST", "0.0.0.0")
port = int(os.getenv("MOCK_PORT", "8443"))
responses_dir = Path(os.getenv("MOCK_RESPONSES_DIR", "tests/fixtures/responses")).resolve()

files = sorted(responses_dir.glob("*.json"))
if not files:
    raise RuntimeError(f"No fixture response files found in {responses_dir}")

responses: list[dict[str, Any]] = []
for file in files:
    with file.open("r", encoding="utf-8") as fh:
        responses.append(json.load(fh))

rotation = itertools.cycle(responses)

app = FastAPI(title="AURA Mock Server", version="0.1.0")

@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": "mock",
        "ready": True,
        "responses_loaded": len(responses),
    }

@app.post("/analyze")
async def analyze(_: dict[str, Any]) -> dict[str, Any]:
    return next(rotation)

@app.websocket("/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        # Stream canned overlay frames until the client disconnects.
        while True:
            await websocket.receive_text()
            await websocket.send_json(next(rotation))
    except WebSocketDisconnect:
        return

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port, log_level="info")
PY
