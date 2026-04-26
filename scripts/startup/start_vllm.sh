#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME="${VLLM_RUNTIME:-docker}" # docker|python
PYTHON_BIN="${PYTHON_BIN:-${VLLM_PYTHON_BIN:-${ROOT_DIR}/.venv-vllm/bin/python}}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
fi
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi
HOST="${VLLM_HOST:-0.0.0.0}"
PORT="${VLLM_PORT:-8000}"
MODEL_DIR="${VLLM_MODEL_DIR:-${ROOT_DIR}/models/qwen2_5_vl_7b}"
MODEL_ID="${VLLM_MODEL_ID:-Qwen/Qwen2.5-VL-7B-Instruct}"
DTYPE="${VLLM_DTYPE:-auto}"
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-8192}"
DEVICE="${VLLM_DEVICE:-cuda}"
LATEST_VLLM_VERSION="${LATEST_VLLM_VERSION:-25.09-py3}"
VLLM_IMAGE="${VLLM_IMAGE:-nvcr.io/nvidia/vllm:${LATEST_VLLM_VERSION}}"
VLLM_CONTAINER_NAME="${VLLM_CONTAINER_NAME:-aura-vllm}"
HF_MODEL_HANDLE="${HF_MODEL_HANDLE:-${MODEL_ID}}"
HF_CACHE_DIR="${HF_CACHE_DIR:-${HOME}/.cache/huggingface}"
VLLM_EXTRA_ARGS="${VLLM_EXTRA_ARGS:-}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
DOCKER_USE_SUDO="${DOCKER_USE_SUDO:-0}"

docker_cmd() {
  if [[ "${DOCKER_USE_SUDO}" == "1" ]]; then
    sudo "${DOCKER_BIN}" "$@"
  else
    "${DOCKER_BIN}" "$@"
  fi
}

if [[ "${RUNTIME}" == "docker" ]]; then
  if ! command -v "${DOCKER_BIN}" >/dev/null 2>&1; then
    echo "Docker is required for VLLM_RUNTIME=docker." >&2
    exit 1
  fi

  if ! docker_cmd info >/dev/null 2>&1; then
    echo "Docker daemon is not reachable for this user." >&2
    echo "Fix options:" >&2
    echo "  1) sudo usermod -aG docker \$USER && newgrp docker" >&2
    echo "  2) run with DOCKER_USE_SUDO=1 (will prompt for password)" >&2
    exit 1
  fi

  echo "Pulling vLLM image ${VLLM_IMAGE} ..."
  docker_cmd pull "${VLLM_IMAGE}"
  docker_cmd rm -f "${VLLM_CONTAINER_NAME}" >/dev/null 2>&1 || true

  model_target="${HF_MODEL_HANDLE}"
  if [[ -d "${MODEL_DIR}" ]]; then
    model_target="/models/$(basename "${MODEL_DIR}")"
  fi

  run_args=(
    run --rm --name "${VLLM_CONTAINER_NAME}" --gpus all
    --ipc=host
    --ulimit memlock=-1
    --ulimit stack=67108864
    -p "${PORT}:8000"
    -e "HF_MODEL_HANDLE=${HF_MODEL_HANDLE}"
    -e "VLLM_USE_V1=1"
    -v "${HF_CACHE_DIR}:/root/.cache/huggingface"
    -v "${ROOT_DIR}/models:/models"
  )

  if [[ -n "${HF_TOKEN:-}" ]]; then
    run_args+=(-e "HF_TOKEN=${HF_TOKEN}")
  fi
  if [[ -n "${HUGGING_FACE_HUB_TOKEN:-}" ]]; then
    run_args+=(-e "HUGGING_FACE_HUB_TOKEN=${HUGGING_FACE_HUB_TOKEN}")
  fi

  run_args+=("${VLLM_IMAGE}" vllm serve "${model_target}" --host 0.0.0.0 --port 8000 --max-model-len "${MAX_MODEL_LEN}" --served-model-name "${MODEL_ID}")
  if [[ -n "${VLLM_EXTRA_ARGS}" ]]; then
    # Allow runtime tuning without script edits, e.g.:
    # VLLM_EXTRA_ARGS="--enforce-eager --gpu-memory-utilization 0.85"
    # shellcheck disable=SC2206
    extra_args=( ${VLLM_EXTRA_ARGS} )
    run_args+=("${extra_args[@]}")
  fi
  echo "Starting vLLM container ${VLLM_CONTAINER_NAME} on ${HOST}:${PORT} with model ${model_target}"
  docker_cmd "${run_args[@]}"
  exit 0
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

VLLM_HELP_ERR="$(mktemp)"
if ! "${PYTHON_BIN}" -m vllm.entrypoints.openai.api_server --help >/dev/null 2>"${VLLM_HELP_ERR}"; then
  echo "vLLM cannot start in the current Python environment." >&2
  if grep -q "libtorch_cuda.so" "${VLLM_HELP_ERR}" 2>/dev/null; then
    echo "Detected CPU-only PyTorch or missing CUDA runtime (libtorch_cuda.so not found)." >&2
    echo "Install a CUDA-enabled torch build in this venv, then rerun." >&2
  else
    echo "Startup check output:" >&2
    cat "${VLLM_HELP_ERR}" >&2
  fi
  rm -f "${VLLM_HELP_ERR}"
  exit 1
fi
rm -f "${VLLM_HELP_ERR}"

MODEL_TARGET="${MODEL_DIR}"
if [[ ! -d "${MODEL_DIR}" ]]; then
  echo "Model directory not found (${MODEL_DIR}); using remote model id ${MODEL_ID}."
  MODEL_TARGET="${MODEL_ID}"
fi

echo "Starting vLLM on ${HOST}:${PORT} with model ${MODEL_TARGET} (device=${DEVICE})"
exec "${PYTHON_BIN}" -m vllm.entrypoints.openai.api_server \
  --host "${HOST}" \
  --port "${PORT}" \
  --model "${MODEL_TARGET}" \
  --served-model-name "${MODEL_ID}" \
  --device "${DEVICE}" \
  --dtype "${DTYPE}" \
  --max-model-len "${MAX_MODEL_LEN}"
