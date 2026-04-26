from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run_eval(eval_script: Path, output_name: str) -> dict:
    cmd = [sys.executable, str(eval_script), "--output", output_name]
    result = subprocess.run(cmd, cwd=str(eval_script.parent), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads((eval_script.parent / output_name).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="A/B compare staged vs compat metrics")
    parser.add_argument("--output", default="ab_report.json", help="Output A/B report file")
    args = parser.parse_args()

    eval_dir = Path(__file__).resolve().parent
    evaluate_script = eval_dir / "evaluate_pipeline.py"
    staged = _run_eval(evaluate_script, "metrics_staged.json")

    # Compat run via temporary env toggle in evaluate script call chain.
    # The evaluate script always uses staged mode; this report includes
    # placeholder compat baseline fields for manual collection.
    compat = {
        "step_transcription_quality": 0.0,
        "algebra_consistency_rate": 0.0,
        "verification_precision_proxy": 0.0,
        "readability_score_proxy": 0.0,
        "note": "Populate by running legacy pipeline benchmark inputs."
    }

    report = {
        "staged": staged,
        "compat": compat,
        "delta": {
            "step_transcription_quality": round(
                staged.get("step_transcription_quality", 0.0) - compat.get("step_transcription_quality", 0.0), 4
            ),
            "algebra_consistency_rate": round(
                staged.get("algebra_consistency_rate", 0.0) - compat.get("algebra_consistency_rate", 0.0), 4
            ),
            "verification_precision_proxy": round(
                staged.get("verification_precision_proxy", 0.0) - compat.get("verification_precision_proxy", 0.0), 4
            ),
            "readability_score_proxy": round(
                staged.get("readability_score_proxy", 0.0) - compat.get("readability_score_proxy", 0.0), 4
            ),
        },
    }
    (eval_dir / args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
