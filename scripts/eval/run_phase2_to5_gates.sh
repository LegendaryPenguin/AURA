#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

cd "${ROOT_DIR}"

echo "Running full baseline gates..."
bash scripts/dev/run_tests.sh

echo "Running phase 2-5 server pipeline/tracking gates..."
"${PYTHON_BIN}" -m pytest \
  tests/unit/api/test_websocket_route.py \
  tests/unit/pipeline/test_streaming_pipeline.py \
  tests/unit/inference/test_audio_backend.py \
  tests/unit/inference/test_segmentation_backends.py \
  tests/unit/inference/test_depth_backends.py \
  tests/unit/tracking/test_tracker_system.py \
  -q

echo "Running strict video-simulation regression gate..."
VIDEO_SIM_VLM_MODEL_ID="${VIDEO_SIM_VLM_MODEL_ID:-Qwen/Qwen2.5-VL-3B-Instruct-AWQ}" \
  "${PYTHON_BIN}" video-simulation/eval/evaluate_pipeline.py --strict --output metrics_strict.json
"${PYTHON_BIN}" - <<'PY'
import json
from pathlib import Path

metrics = json.loads(Path("video-simulation/eval/metrics_strict.json").read_text(encoding="utf-8"))
sample_count = int(metrics.get("sample_count", 0))
processed_count = int(metrics.get("processed_count", 0))
strict_fail_count = int(metrics.get("strict_fail_count", 0))
if processed_count < sample_count or strict_fail_count > 0:
    raise SystemExit(
        f"Strict video-simulation gate failed: processed={processed_count}/{sample_count}, strict_fail_count={strict_fail_count}"
    )
PY

echo "Phase 2-5 gates completed."
