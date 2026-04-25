#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-120}"
SLEEP_SECONDS="${SLEEP_SECONDS:-2}"

VLLM_HEALTH_URL="${VLLM_HEALTH_URL:-http://127.0.0.1:8000/health}"
SAM2_HEALTH_URL="${SAM2_HEALTH_URL:-http://127.0.0.1:8001/health}"
SERVER_HEALTH_URL="${SERVER_HEALTH_URL:-https://127.0.0.1:8443/health}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

wait_for_endpoint() {
  local name="$1"
  local url="$2"
  local elapsed=0

  while (( elapsed < MAX_WAIT_SECONDS )); do
    if "${PYTHON_BIN}" - "$url" <<'PY'
import ssl
import sys
import urllib.request

url = sys.argv[1]
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
handler = opener.open if url.startswith("https://") else urllib.request.urlopen
try:
    with handler(url, timeout=2) as response:
        if 200 <= response.getcode() < 300:
            sys.exit(0)
except Exception:
    pass
sys.exit(1)
PY
    then
      echo "${name} is healthy at ${url}"
      return 0
    fi

    sleep "${SLEEP_SECONDS}"
    elapsed=$((elapsed + SLEEP_SECONDS))
  done

  echo "Timed out waiting for ${name} at ${url}" >&2
  return 1
}

wait_for_endpoint "vLLM" "${VLLM_HEALTH_URL}"
wait_for_endpoint "SAM2 service" "${SAM2_HEALTH_URL}"
wait_for_endpoint "AURA server" "${SERVER_HEALTH_URL}"

echo "All services are healthy."
