#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODELS_DIR="${ROOT_DIR}/models"

QWEN_MODEL="${QWEN_MODEL:-Qwen/Qwen2.5-VL-7B-Instruct}"
SAM2_MODEL="${SAM2_MODEL:-facebook/sam2-hiera-large}"
DEPTH_MODEL="${DEPTH_MODEL:-depth-anything/Depth-Anything-V2-Large}"

mkdir -p "${MODELS_DIR}"

if command -v hf >/dev/null 2>&1; then
  HF_CMD="hf"
elif command -v huggingface-cli >/dev/null 2>&1; then
  HF_CMD="huggingface-cli"
else
  cat <<EOF
huggingface CLI is not installed.
Install it with:
  python3 -m pip install huggingface_hub
Then re-run this script.
EOF
  exit 1
fi

download_model() {
  local model_id="$1"
  local output_dir="$2"

  # hf/huggingface-cli download is resumable and idempotent; always call it to
  # avoid false positives from partially downloaded directories.
  echo "Syncing ${model_id} -> ${output_dir}"
  mkdir -p "${output_dir}"
  if [[ "${HF_CMD}" == "hf" ]]; then
    hf download "${model_id}" --local-dir "${output_dir}"
  else
    huggingface-cli download "${model_id}" --local-dir "${output_dir}" --local-dir-use-symlinks False
  fi
}

download_model "${QWEN_MODEL}" "${MODELS_DIR}/qwen2_5_vl_7b"
download_model "${SAM2_MODEL}" "${MODELS_DIR}/sam2"
download_model "${DEPTH_MODEL}" "${MODELS_DIR}/depth_anything_v2"

echo "Model download step completed."
