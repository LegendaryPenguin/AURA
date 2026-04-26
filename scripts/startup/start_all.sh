#!/usr/bin/env bash

set -euo pipefail

# Startup logging behavior:
# - Default (quiet): readiness heartbeats + sparse diagnostics.
# - Stream mode: set AURA_STREAM_STARTUP_LOGS=1 to follow service logs in real time.
# Note: dockerized vLLM logs can still appear in bursts depending on runtime buffering.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACT_DIR="${AURA_STACK_ARTIFACT_DIR:-${ROOT_DIR}/artifacts}"

STACK_MODE="real"
VLLM_RUNTIME="${VLLM_RUNTIME:-docker}" # docker|python
FRONTEND_PORT="${AURA_FRONTEND_PORT:-5173}"
FRONTEND_HOST="${AURA_FRONTEND_HOST:-0.0.0.0}"
BACKEND_HEALTH_URL_REAL="${AURA_BACKEND_HEALTH_URL_REAL:-http://127.0.0.1:9443/health}"
REAL_BACKEND_PORT="${AURA_REAL_BACKEND_PORT:-9443}"
VLLM_HEALTH_URL="${AURA_VLLM_HEALTH_URL:-http://127.0.0.1:8000/health}"
SAM2_HEALTH_URL="${AURA_SAM2_HEALTH_URL:-http://127.0.0.1:8001/health}"
VLLM_STARTUP_TIMEOUT_SECONDS="${AURA_VLLM_STARTUP_TIMEOUT_SECONDS:-900}"
VLM_HTTP_TIMEOUT_MS="${AURA_VLM_TIMEOUT_MS:-60000}"
VLM_MODEL_ID="${AURA_VLM_MODEL_ID:-/models/qwen2_5_vl_7b}"
VLM_TARGET_DIM="${AURA_VLM_TARGET_DIM:-512}"
VLM_MAX_TOKENS="${AURA_VLM_MAX_TOKENS:-220}"
FRONTEND_HEALTH_URL="${AURA_FRONTEND_HEALTH_URL:-http://127.0.0.1:${FRONTEND_PORT}}"
PUBLIC_LINK_TIMEOUT_SECONDS="${AURA_PUBLIC_LINK_TIMEOUT_SECONDS:-25}"
PUBLIC_LINK_FILE="${AURA_PUBLIC_LINK_FILE:-${ARTIFACT_DIR}/public-link.txt}"
PUBLIC_LINK_LOG="${AURA_PUBLIC_LINK_LOG:-${ARTIFACT_DIR}/public-link.log}"
FRONTEND_LOG="${AURA_FRONTEND_LOG:-${ARTIFACT_DIR}/frontend.log}"
BACKEND_LOG="${AURA_BACKEND_LOG:-${ARTIFACT_DIR}/backend.log}"
VLLM_LOG="${AURA_VLLM_LOG:-${ARTIFACT_DIR}/vllm.log}"
SAM2_LOG="${AURA_SAM2_LOG:-${ARTIFACT_DIR}/sam2.log}"
STREAM_STARTUP_LOGS="${AURA_STREAM_STARTUP_LOGS:-0}"
STARTUP_HEARTBEAT_SECONDS="${AURA_STARTUP_HEARTBEAT_SECONDS:-5}"
STALL_LOG_DIGEST_SECONDS="${AURA_STALL_LOG_DIGEST_SECONDS:-20}"
STALL_LOG_DIGEST_LINES="${AURA_STALL_LOG_DIGEST_LINES:-25}"

FRONTEND_PID=""
BACKEND_PID=""
VLLM_PID=""
SAM2_PID=""
TUNNEL_PID=""
FRONTEND_EXTERNAL="0"
LOG_TAIL_PIDS=()

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
  local log_file="${4:-}"
  local watched_pid="${5:-}"
  local elapsed=0
  local next_log_at="${STARTUP_HEARTBEAT_SECONDS}"
  local digest_printed=0

  echo "Waiting for ${name} at ${url} (timeout ${timeout}s)..."
  while (( elapsed < timeout )); do
    if curl -ksS -m 2 "${url}" >/dev/null 2>&1; then
      echo "${name} healthy at ${url}"
      return 0
    fi

    if [[ -n "${watched_pid}" ]] && ! kill -0 "${watched_pid}" >/dev/null 2>&1; then
      echo "${name} process exited before becoming healthy." >&2
      if [[ -n "${log_file}" && -f "${log_file}" ]]; then
        echo "Last ${name} log lines:" >&2
        tail -n 40 "${log_file}" >&2 || true
      fi
      return 1
    fi

    if (( elapsed == 0 || elapsed >= next_log_at )); then
      echo "  ...${name} not ready yet (${elapsed}s/${timeout}s)"
      next_log_at=$((next_log_at + STARTUP_HEARTBEAT_SECONDS))
    fi

    if (( digest_printed == 0 && elapsed >= STALL_LOG_DIGEST_SECONDS )) && [[ -n "${log_file}" && -f "${log_file}" ]]; then
      echo "  --- ${name} still starting; recent log snapshot ---"
      tail -n "${STALL_LOG_DIGEST_LINES}" "${log_file}" 2>/dev/null || true
      echo "  --- end snapshot (${log_file}) ---"
      digest_printed=1
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  echo "Timed out waiting for ${name} at ${url}" >&2
  if [[ -n "${log_file}" && -f "${log_file}" ]]; then
    echo "Last ${name} log lines:" >&2
    tail -n 30 "${log_file}" >&2 || true
  fi
  return 1
}

stream_logs_enabled() {
  case "${STREAM_STARTUP_LOGS}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

start_log_stream() {
  local prefix="$1"
  local log_file="$2"

  if ! stream_logs_enabled; then
    return 0
  fi

  touch "${log_file}"
  (
    tail -n 0 -F "${log_file}" 2>/dev/null | while IFS= read -r line; do
      printf '[%s] %s\n' "${prefix}" "${line}"
    done
  ) &
  LOG_TAIL_PIDS+=("$!")
}

cleanup() {
  for pid in "${LOG_TAIL_PIDS[@]}"; do
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill "${pid}" >/dev/null 2>&1 || true
    fi
  done
  for pid in "${TUNNEL_PID}" "${BACKEND_PID}" "${SAM2_PID}" "${VLLM_PID}" "${FRONTEND_PID}"; do
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill "${pid}" >/dev/null 2>&1 || true
    fi
  done
}

cleanup_on_interrupt() {
  if [[ -n "${TUNNEL_PID}" ]] && kill -0 "${TUNNEL_PID}" >/dev/null 2>&1; then
    kill "${TUNNEL_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" >/dev/null 2>&1; then
    kill "${FRONTEND_PID}" >/dev/null 2>&1 || true
  fi
  echo "Stopped orchestrator/tunnel. Backend services remain running."
}

forward_term() {
  cleanup_on_interrupt
  trap - EXIT
  exit 0
}

start_frontend() {
  if curl -ksS -m 2 "${FRONTEND_HEALTH_URL}" >/dev/null 2>&1; then
    echo "Frontend already running at ${FRONTEND_HEALTH_URL}; reusing existing process."
    FRONTEND_EXTERNAL="1"
    FRONTEND_PID=""
    return 0
  fi

  echo "Starting frontend on ${FRONTEND_HOST}:${FRONTEND_PORT} ..."
  : > "${FRONTEND_LOG}"
  (
    cd "${ROOT_DIR}/client"
    export VITE_API_TARGET_REAL="${VITE_API_TARGET_REAL:-http://localhost:${REAL_BACKEND_PORT}}"
    export VITE_REQUEST_TIMEOUT_MS="${VITE_REQUEST_TIMEOUT_MS:-60000}"
    npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" --strictPort
  ) >"${FRONTEND_LOG}" 2>&1 &
  FRONTEND_PID="$!"
  start_log_stream "frontend" "${FRONTEND_LOG}"
  wait_for_url "Frontend" "${FRONTEND_HEALTH_URL}" 35 "${FRONTEND_LOG}"
}

start_backend() {
  start_real_dependencies() {
    if curl -ksS -m 2 "${VLLM_HEALTH_URL}" >/dev/null 2>&1; then
      echo "vLLM already running at ${VLLM_HEALTH_URL}; reusing existing process."
    else
      echo "Starting vLLM service on :8000 ..."
      : > "${VLLM_LOG}"
      (
        cd "${ROOT_DIR}"
        export PYTHONUNBUFFERED=1
        VLLM_MODEL_ID="${VLM_MODEL_ID}" VLLM_MODEL_DIR="${ROOT_DIR}/models/qwen2_5_vl_7b" HF_MODEL_HANDLE="${VLM_MODEL_ID}" bash scripts/startup/start_vllm.sh
      ) >"${VLLM_LOG}" 2>&1 &
      VLLM_PID="$!"
      start_log_stream "vllm" "${VLLM_LOG}"
      wait_for_url "vLLM" "${VLLM_HEALTH_URL}" "${VLLM_STARTUP_TIMEOUT_SECONDS}" "${VLLM_LOG}" "${VLLM_PID}"
    fi

    if curl -ksS -m 2 "${SAM2_HEALTH_URL}" >/dev/null 2>&1; then
      echo "SAM2 service already running at ${SAM2_HEALTH_URL}; reusing existing process."
    else
      echo "Starting SAM2 service on :8001 ..."
      : > "${SAM2_LOG}"
      (
        cd "${ROOT_DIR}"
        export PYTHONUNBUFFERED=1
        bash scripts/startup/start_sam2_service.sh
      ) >"${SAM2_LOG}" 2>&1 &
      SAM2_PID="$!"
      start_log_stream "sam2" "${SAM2_LOG}"
      wait_for_url "SAM2 service" "${SAM2_HEALTH_URL}" 35 "${SAM2_LOG}" "${SAM2_PID}"
    fi
  }

  start_real_dependencies
  if curl -ksS -m 2 "${BACKEND_HEALTH_URL_REAL}" >/dev/null 2>&1; then
    echo "Real backend already running at ${BACKEND_HEALTH_URL_REAL}; reusing existing process."
    BACKEND_PID=""
  else
    echo "Starting real backend on :${REAL_BACKEND_PORT} ..."
    : > "${BACKEND_LOG}"
    (
      cd "${ROOT_DIR}"
      export PYTHONUNBUFFERED=1
      AURA_ENABLE_PUBLIC_LINK=0 AURA_DISABLE_SSL=1 AURA_PORT="${REAL_BACKEND_PORT}" \
      AURA_VLM_TIMEOUT_MS="${VLM_HTTP_TIMEOUT_MS}" AURA_VLM_MODEL_ID="${VLM_MODEL_ID}" \
      AURA_VLM_TARGET_DIM="${VLM_TARGET_DIM}" AURA_VLM_MAX_TOKENS="${VLM_MAX_TOKENS}" \
      bash scripts/startup/start_server.sh
    ) >"${BACKEND_LOG}" 2>&1 &
    BACKEND_PID="$!"
    start_log_stream "backend" "${BACKEND_LOG}"
    wait_for_url "Real backend" "${BACKEND_HEALTH_URL_REAL}" 45 "${BACKEND_LOG}"
  fi
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

ensure_vllm_runtime_ready() {
  if [[ "${VLLM_RUNTIME}" != "docker" ]]; then
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required for real backend when VLLM_RUNTIME=docker." >&2
    exit 1
  fi
  if [[ "${DOCKER_USE_SUDO:-0}" == "1" ]]; then
    if sudo docker info >/dev/null 2>&1; then
      return 0
    fi
    echo "DOCKER_USE_SUDO=1 was set, but sudo docker access failed." >&2
    echo "Verify your sudo password or add docker group access." >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is not reachable for this user." >&2
    echo "Run one-time fix then restart terminal:" >&2
    echo "  sudo usermod -aG docker \$USER" >&2
    echo "  newgrp docker" >&2
    echo "Or run this script with DOCKER_USE_SUDO=1 (password prompt expected)." >&2
    exit 1
  fi
}

trap cleanup EXIT
trap forward_term INT TERM

ensure_vllm_runtime_ready
start_frontend
start_backend
start_tunnel

echo ""
echo "Stack is ready."
echo "- Stack mode  : ${STACK_MODE}"
echo "- Frontend log: ${FRONTEND_LOG}"
echo "- Backend log : ${BACKEND_LOG}"
echo "- Tunnel log  : ${PUBLIC_LINK_LOG}"
echo "- Backend map : real=http://127.0.0.1:${REAL_BACKEND_PORT}"
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

  if [[ -z "${BACKEND_PID}" ]] || ! kill -0 "${BACKEND_PID}" >/dev/null 2>&1; then
    if ! curl -ksS -m 2 "${BACKEND_HEALTH_URL_REAL}" >/dev/null 2>&1; then
      echo "Real backend process exited; shutting down stack..."
      break
    fi
  fi

  if [[ -n "${VLLM_PID}" ]] && ! kill -0 "${VLLM_PID}" >/dev/null 2>&1; then
    echo "vLLM process exited; shutting down stack..."
    break
  fi
  if [[ -n "${SAM2_PID}" ]] && ! kill -0 "${SAM2_PID}" >/dev/null 2>&1; then
    echo "SAM2 process exited; shutting down stack..."
    break
  fi

  if [[ -z "${TUNNEL_PID}" ]] || ! kill -0 "${TUNNEL_PID}" >/dev/null 2>&1; then
    echo "Tunnel process exited; restarting tunnel..."
    start_tunnel || true
  fi

  sleep 2
done
