#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VLLM_VENV_DIR="${VLLM_VENV_DIR:-${ROOT_DIR}/.venv-vllm}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu126}"
VLLM_VERSION="${VLLM_VERSION:-0.19.1}"
TORCH_VERSION="${TORCH_VERSION:-2.10.0+cu126}"
TORCHVISION_VERSION="${TORCHVISION_VERSION:-0.25.0+cu126}"
TORCHAUDIO_VERSION="${TORCHAUDIO_VERSION:-2.10.0+cu126}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

echo "Creating vLLM virtualenv at ${VLLM_VENV_DIR}"
"${PYTHON_BIN}" -m venv "${VLLM_VENV_DIR}"

VENV_PYTHON="${VLLM_VENV_DIR}/bin/python"
if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Failed to create vLLM venv python at ${VENV_PYTHON}" >&2
  exit 1
fi

echo "Installing vLLM runtime dependencies into ${VLLM_VENV_DIR}"
"${VENV_PYTHON}" -m pip install --upgrade pip "setuptools>=77.0.3,<81.0.0"
"${VENV_PYTHON}" -m pip install --index-url "${TORCH_INDEX_URL}" \
  "torch==${TORCH_VERSION}" "torchvision==${TORCHVISION_VERSION}" "torchaudio==${TORCHAUDIO_VERSION}"
"${VENV_PYTHON}" -m pip install "numpy>=1.26,<2.3" "vllm==${VLLM_VERSION}"

echo "vLLM dependencies installed."
echo "Use VLLM_PYTHON_BIN=${VENV_PYTHON} if you need explicit overrides."
