#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

cd "${ROOT_DIR}"

echo "Running core test gates..."
bash scripts/dev/run_tests.sh

echo "Running latency gate (single-model endpoint)..."
"${PYTHON_BIN}" scripts/eval/latency_gate.py --output artifacts/latency_gate.json

echo "Running model parity gate..."
"${PYTHON_BIN}" scripts/eval/model_parity_gate.py --output artifacts/model_parity_gate.json --output-dir artifacts/parity

echo "Running strict video-simulation eval..."
VIDEO_SIM_VLM_MODEL_ID="${VIDEO_SIM_VLM_MODEL_ID:-Qwen/Qwen2.5-VL-3B-Instruct-AWQ}" \
  "${PYTHON_BIN}" video-simulation/eval/evaluate_pipeline.py --strict --output metrics_strict.json

echo "Phase 1 gate scripts completed."
