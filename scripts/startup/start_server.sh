#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${AURA_HOST:-0.0.0.0}"
PORT="${AURA_PORT:-8443}"
APP_MODULE="${AURA_APP_MODULE:-server.main:app}"
CERT_FILE="${AURA_SSL_CERTFILE:-${ROOT_DIR}/config/ssl/localhost+ip.pem}"
KEY_FILE="${AURA_SSL_KEYFILE:-${ROOT_DIR}/config/ssl/localhost+ip-key.pem}"
DISABLE_SSL="${AURA_DISABLE_SSL:-0}"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

if ! "${PYTHON_BIN}" -m uvicorn --help >/dev/null 2>&1; then
  echo "uvicorn is required in the selected Python environment (${PYTHON_BIN})." >&2
  exit 1
fi

if [[ "${DISABLE_SSL}" != "1" ]] && [[ ! -f "${CERT_FILE}" || ! -f "${KEY_FILE}" ]]; then
  echo "SSL files not found; starting without SSL." >&2
  echo "Expected cert: ${CERT_FILE}" >&2
  echo "Expected key : ${KEY_FILE}" >&2
  echo "Run scripts/setup/setup_ssl.sh if you want HTTPS on backend." >&2
  DISABLE_SSL="1"
fi

if [[ "${DISABLE_SSL}" == "1" ]]; then
  echo "Starting FastAPI app ${APP_MODULE} on http://${HOST}:${PORT}"
  exec "${PYTHON_BIN}" -m uvicorn "${APP_MODULE}" \
    --host "${HOST}" \
    --port "${PORT}" \
    --proxy-headers
fi

echo "Starting FastAPI app ${APP_MODULE} on https://${HOST}:${PORT}"
exec "${PYTHON_BIN}" -m uvicorn "${APP_MODULE}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --ssl-certfile "${CERT_FILE}" \
  --ssl-keyfile "${KEY_FILE}" \
  --proxy-headers
