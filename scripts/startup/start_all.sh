#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACT_DIR="${AURA_STACK_ARTIFACT_DIR:-${ROOT_DIR}/artifacts}"

STACK_MODE="${AURA_STACK_MODE:-mock}" # mock|real
FRONTEND_PORT="${AURA_FRONTEND_PORT:-5173}"
FRONTEND_HOST="${AURA_FRONTEND_HOST:-0.0.0.0}"
BACKEND_HEALTH_URL_MOCK="${AURA_BACKEND_HEALTH_URL_MOCK:-http://127.0.0.1:8443/health}"
BACKEND_HEALTH_URL_REAL="${AURA_BACKEND_HEALTH_URL_REAL:-https://127.0.0.1:8443/health}"
FRONTEND_HEALTH_URL="${AURA_FRONTEND_HEALTH_URL:-http://127.0.0.1:${FRONTEND_PORT}}"
PUBLIC_LINK_TIMEOUT_SECONDS="${AURA_PUBLIC_LINK_TIMEOUT_SECONDS:-25}"
PUBLIC_LINK_FILE="${AURA_PUBLIC_LINK_FILE:-${ARTIFACT_DIR}/public-link.txt}"
PUBLIC_LINK_LOG="${AURA_PUBLIC_LINK_LOG:-${ARTIFACT_DIR}/public-link.log}"
FRONTEND_LOG="${AURA_FRONTEND_LOG:-${ARTIFACT_DIR}/frontend.log}"
BACKEND_LOG="${AURA_BACKEND_LOG:-${ARTIFACT_DIR}/backend.log}"

FRONTEND_PID=""
BACKEND_PID=""
TUNNEL_PID=""
FRONTEND_EXTERNAL="0"
BACKEND_EXTERNAL="0"

mkdir -p "${ARTIFACT_DIR}"

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Required command not found: ${cmd}" >&2
    exit 1
  fi
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local timeout="${3:-30}"
  local elapsed=0

  while (( elapsed < timeout )); do
    if curl -ksS -m 2 "${url}" >/dev/null 2>&1; then
      echo "${name} healthy at ${url}"
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  echo "Timed out waiting for ${name} at ${url}" >&2
  return 1
}

cleanup() {
  for pid in "${TUNNEL_PID}" "${BACKEND_PID}" "${FRONTEND_PID}"; do
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill "${pid}" >/dev/null 2>&1 || true
    fi
  done
}

forward_term() {
  cleanup
}

start_frontend() {
  if curl -ksS -m 2 "${FRONTEND_HEALTH_URL}" >/dev/null 2>&1; then
    echo "Frontend already running at ${FRONTEND_HEALTH_URL}; reusing existing process."
    FRONTEND_EXTERNAL="1"
    FRONTEND_PID=""
    return 0
  fi

  echo "Starting frontend on ${FRONTEND_HOST}:${FRONTEND_PORT} ..."
  (
    cd "${ROOT_DIR}/client"
    npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" --strictPort
  ) >"${FRONTEND_LOG}" 2>&1 &
  FRONTEND_PID="$!"
  wait_for_url "Frontend" "${FRONTEND_HEALTH_URL}" 35
}

start_backend() {
  case "${STACK_MODE}" in
    mock)
      if curl -ksS -m 2 "${BACKEND_HEALTH_URL_MOCK}" >/dev/null 2>&1; then
        echo "Mock backend already running at ${BACKEND_HEALTH_URL_MOCK}; reusing existing process."
        BACKEND_EXTERNAL="1"
        BACKEND_PID=""
        return 0
      fi
      echo "Starting mock backend on :8443 ..."
      (
        cd "${ROOT_DIR}"
        bash scripts/dev/run_mock_server.sh
      ) >"${BACKEND_LOG}" 2>&1 &
      BACKEND_PID="$!"
      wait_for_url "Mock backend" "${BACKEND_HEALTH_URL_MOCK}" 35
      ;;
    real)
      echo "Starting real backend on :8443 ..."
      (
        cd "${ROOT_DIR}"
        AURA_ENABLE_PUBLIC_LINK=0 bash scripts/startup/start_server.sh
      ) >"${BACKEND_LOG}" 2>&1 &
      BACKEND_PID="$!"
      wait_for_url "Real backend" "${BACKEND_HEALTH_URL_REAL}" 45
      ;;
    *)
      echo "Invalid AURA_STACK_MODE='${STACK_MODE}'. Use 'mock' or 'real'." >&2
      exit 1
      ;;
  esac
}

start_tunnel() {
  if [[ -n "${TUNNEL_PID}" ]] && kill -0 "${TUNNEL_PID}" >/dev/null 2>&1; then
    kill "${TUNNEL_PID}" >/dev/null 2>&1 || true
  fi

  : > "${PUBLIC_LINK_LOG}"
  echo "Starting public tunnel for localhost:${FRONTEND_PORT} ..."
  ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 \
    -R 80:localhost:"${FRONTEND_PORT}" \
    nokey@localhost.run >"${PUBLIC_LINK_LOG}" 2>&1 &
  TUNNEL_PID="$!"

  local deadline=$((SECONDS + PUBLIC_LINK_TIMEOUT_SECONDS))
  local public_url=""
  local tunnel_line=""
  while (( SECONDS < deadline )); do
    tunnel_line="$(grep -m 1 "tunneled with tls termination, https://" "${PUBLIC_LINK_LOG}" || true)"
    if [[ -n "${tunnel_line}" ]]; then
      public_url="$(printf '%s\n' "${tunnel_line}" | sed -n 's/.*\(https:\/\/[^ ]*\).*/\1/p')"
    fi
    if [[ -n "${public_url}" ]]; then
      break
    fi
    sleep 1
  done

  if [[ -z "${public_url}" ]]; then
    echo "Could not detect public URL from tunnel logs within ${PUBLIC_LINK_TIMEOUT_SECONDS}s." >&2
    echo "Inspect logs: ${PUBLIC_LINK_LOG}" >&2
    return 1
  fi

  printf '%s\n' "${public_url}" | tee "${PUBLIC_LINK_FILE}"
  echo "Public URL saved at ${PUBLIC_LINK_FILE}"

  if command -v npx >/dev/null 2>&1; then
    echo "QR code for phone:"
    npx --yes qrcode-terminal "${public_url}" || true
  else
    echo "npx not found; skipping QR print."
  fi

  # Ensure tunnel endpoint is usable through Vite host checks.
  if ! curl -sS -m 8 "${public_url}/api/health" >/dev/null 2>&1; then
    echo "Warning: tunnel URL opened but /api/health check failed. Check logs and running services." >&2
  fi
}

require_cmd npm
require_cmd ssh
require_cmd curl

trap cleanup EXIT
trap forward_term INT TERM

start_frontend
start_backend
start_tunnel

echo ""
echo "Stack is ready."
echo "- Frontend log: ${FRONTEND_LOG}"
echo "- Backend log : ${BACKEND_LOG}"
echo "- Tunnel log  : ${PUBLIC_LINK_LOG}"
echo "Press Ctrl+C to stop all."

# Keep stack alive as long as frontend and backend remain healthy.
# Tunnel can drop intermittently; restart it automatically.
while true; do
  if [[ "${FRONTEND_EXTERNAL}" == "1" ]]; then
    if ! curl -ksS -m 2 "${FRONTEND_HEALTH_URL}" >/dev/null 2>&1; then
      echo "Frontend at ${FRONTEND_HEALTH_URL} is no longer reachable; shutting down stack..."
      break
    fi
  else
    if [[ -z "${FRONTEND_PID}" ]] || ! kill -0 "${FRONTEND_PID}" >/dev/null 2>&1; then
      echo "Frontend process exited; shutting down stack..."
      break
    fi
  fi

  if [[ "${BACKEND_EXTERNAL}" == "1" ]]; then
    if ! curl -ksS -m 2 "${BACKEND_HEALTH_URL_MOCK}" >/dev/null 2>&1; then
      echo "Backend at ${BACKEND_HEALTH_URL_MOCK} is no longer reachable; shutting down stack..."
      break
    fi
  else
    if [[ -z "${BACKEND_PID}" ]] || ! kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
      echo "Backend process exited; shutting down stack..."
      break
    fi
  fi

  if [[ -z "${TUNNEL_PID}" ]] || ! kill -0 "${TUNNEL_PID}" >/dev/null 2>&1; then
    echo "Tunnel process exited; restarting tunnel..."
    start_tunnel || true
  fi

  sleep 2
done
