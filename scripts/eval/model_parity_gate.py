from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


MODELS: dict[str, str] = {
    "qwen3b": "Qwen/Qwen2.5-VL-3B-Instruct-AWQ",
    "qwen7b": "Qwen/Qwen2.5-VL-7B-Instruct",
    "moondream2": "vikhyatk/moondream2",
}


def _run_latency_for_model(model_key: str, model_id: str, args: argparse.Namespace) -> dict[str, Any]:
    output_file = Path(args.output_dir) / f"latency_{model_key}.json"
    cmd = [
        sys.executable,
        str(Path(__file__).with_name("latency_gate.py")),
        "--endpoint",
        args.endpoint,
        "--image",
        args.image,
        "--query",
        args.query,
        "--warmups",
        str(args.warmups),
        "--samples",
        str(args.samples),
        "--timeout-s",
        str(args.timeout_s),
        "--p95-threshold-ms",
        str(args.p95_threshold_ms),
        "--output",
        str(output_file),
    ]
    env = os.environ.copy()
    env["AURA_VLM_MODEL_ID"] = model_id
    completed = subprocess.run(cmd, check=False, env=env, capture_output=True, text=True)
    payload = json.loads(output_file.read_text(encoding="utf-8")) if output_file.exists() else {}
    payload["model_key"] = model_key
    payload["model_id"] = model_id
    payload["runner_exit_code"] = completed.returncode
    payload["runner_stdout"] = completed.stdout[-2000:]
    payload["runner_stderr"] = completed.stderr[-2000:]
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run model parity gate over latency results.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:9443")
    parser.add_argument("--image", default="tests/fixtures/images/benchmark_object_01.ppm")
    parser.add_argument("--query", default="Identify the main object in this image.")
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--p95-threshold-ms", type=float, default=2000.0)
    parser.add_argument("--output-dir", default="artifacts/parity")
    parser.add_argument("--output", default="artifacts/model_parity_gate.json")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    results = {k: _run_latency_for_model(k, model_id, args) for k, model_id in MODELS.items()}
    parity_pass = all(bool(item.get("pass")) for item in results.values())
    summary = {"endpoint": args.endpoint, "models": results, "pass": parity_pass}

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if args.enforce and not parity_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
