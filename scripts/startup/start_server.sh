#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${AURA_HOST:-0.0.0.0}"
PORT="${AURA_PORT:-8443}"
APP_MODULE="${AURA_APP_MODULE:-server.main:app}"
CERT_FILE="${AURA_SSL_CERTFILE:-${ROOT_DIR}/config/ssl/localhost+ip.pem}"
KEY_FILE="${AURA_SSL_KEYFILE:-${ROOT_DIR}/config/ssl/localhost+ip-key.pem}"

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn is required but not installed." >&2
  exit 1
fi

if [[ ! -f "${CERT_FILE}" || ! -f "${KEY_FILE}" ]]; then
  echo "SSL files not found." >&2
  echo "Expected cert: ${CERT_FILE}" >&2
  echo "Expected key : ${KEY_FILE}" >&2
  echo "Run scripts/setup/setup_ssl.sh first." >&2
  exit 1
fi

echo "Starting FastAPI app ${APP_MODULE} on https://${HOST}:${PORT}"
exec uvicorn "${APP_MODULE}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --ssl-certfile "${CERT_FILE}" \
  --ssl-keyfile "${KEY_FILE}" \
  --proxy-headers
