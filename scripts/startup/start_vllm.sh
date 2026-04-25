#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi
HOST="${VLLM_HOST:-0.0.0.0}"
PORT="${VLLM_PORT:-8000}"
MODEL_DIR="${VLLM_MODEL_DIR:-${ROOT_DIR}/models/qwen2_5_vl_7b}"
MODEL_ID="${VLLM_MODEL_ID:-Qwen/Qwen2.5-VL-7B-Instruct}"
DTYPE="${VLLM_DTYPE:-auto}"
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-4096}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

if ! "${PYTHON_BIN}" -m vllm.entrypoints.openai.api_server --help >/dev/null 2>&1; then
  echo "vLLM is not available in the current Python environment." >&2
  echo "Install vllm first, then rerun." >&2
  exit 1
fi

MODEL_TARGET="${MODEL_DIR}"
if [[ ! -d "${MODEL_DIR}" ]]; then
  echo "Model directory not found (${MODEL_DIR}); using remote model id ${MODEL_ID}."
  MODEL_TARGET="${MODEL_ID}"
fi

echo "Starting vLLM on ${HOST}:${PORT} with model ${MODEL_TARGET}"
exec "${PYTHON_BIN}" -m vllm.entrypoints.openai.api_server \
  --host "${HOST}" \
  --port "${PORT}" \
  --model "${MODEL_TARGET}" \
  --dtype "${DTYPE}" \
  --max-model-len "${MAX_MODEL_LEN}"
