#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

terminate_matching() {
  local pattern="$1"
  local label="$2"
  local pids
  pids="$(pgrep -f "${pattern}" || true)"
  if [[ -z "${pids}" ]]; then
    echo "No ${label} processes found."
    return 0
  fi

  echo "Stopping ${label}: ${pids}"
  kill ${pids} >/dev/null 2>&1 || true
}

echo "Stopping AURA frontend/backend/tunnel processes..."

# Vite frontend.
terminate_matching "${ROOT_DIR}/client.*vite" "frontend (vite)"
terminate_matching "npm run dev -- --host" "frontend npm wrapper"

# Mock backend and real backend entrypoints.
terminate_matching "scripts/dev/run_mock_server.sh" "mock backend launcher"
terminate_matching "server.main:app" "real backend (uvicorn)"
terminate_matching "scripts/startup/start_server.sh" "real backend launcher"
terminate_matching "vllm.entrypoints.openai.api_server" "vLLM service"
terminate_matching "scripts/startup/start_sam2_service.sh" "SAM2 service launcher"
terminate_matching "AURA SAM2 Service" "SAM2 service"

# Stack orchestrator and tunnel.
terminate_matching "scripts/startup/start_all.sh" "stack orchestrator"
terminate_matching "nokey@localhost.run" "localhost.run tunnel"

if command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -x "aura-vllm" >/dev/null 2>&1; then
    echo "Stopping vLLM container: aura-vllm"
    docker rm -f aura-vllm >/dev/null 2>&1 || true
  fi
fi

echo "Done."
