from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from statistics import mean
from typing import Any


def _run_pipeline(repo_root: Path, image_path: Path, mode: str) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(repo_root / "pipeline" / "run_pipeline.py"),
        "--image",
        str(image_path),
        "--skip-render",
        "--pipeline-mode",
        mode,
    ]
    result = subprocess.run(cmd, cwd=str(repo_root / "pipeline"), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr.strip() or result.stdout.strip()}
    out_dir = repo_root / "outputs"
    artifacts = sorted(out_dir.glob("ocr_result_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not artifacts:
        return {"ok": False, "error": "no_artifact_generated"}
    payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
    return {"ok": True, "artifact_path": str(artifacts[0]), "artifact": payload}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate staged video-simulation pipeline")
    parser.add_argument("--samples", default="samples.json", help="Path to evaluation samples manifest")
    parser.add_argument("--output", default="metrics.json", help="Output metrics JSON path")
    args = parser.parse_args()

    eval_dir = Path(__file__).resolve().parent
    root = eval_dir.parent
    samples_payload = json.loads((eval_dir / args.samples).read_text(encoding="utf-8"))
    samples = samples_payload.get("samples", [])
    rows: list[dict[str, Any]] = []
    transcription_scores: list[float] = []
    consistency_scores: list[float] = []
    verified_flags: list[float] = []
    readability_scores: list[float] = []

    for sample in samples:
        image = root / str(sample["image"])
        staged = _run_pipeline(root, image, "staged")
        if not staged["ok"]:
            rows.append({"id": sample["id"], "ok": False, "error": staged["error"]})
            continue
        art = staged["artifact"]
        normalize = art.get("normalize", {})
        verify = art.get("verify", {})
        narrate = art.get("narrate", {})
        q = float(normalize.get("avg_quality", 0.0))
        transitions = verify.get("transitions", [])
        eq_count = sum(1 for t in transitions if t.get("status") == "equivalent")
        consistency = (eq_count / len(transitions)) if transitions else 0.0
        verified = 1.0 if verify.get("is_verified", False) else 0.0
        readability = {"low": 0.3, "medium": 0.65, "high": 0.9}.get(narrate.get("render_quality_grade", "low"), 0.3)
        transcription_scores.append(q)
        consistency_scores.append(consistency)
        verified_flags.append(verified)
        readability_scores.append(readability)
        rows.append(
            {
                "id": sample["id"],
                "ok": True,
                "artifact": staged["artifact_path"],
                "transcription_quality": q,
                "algebra_consistency_rate": consistency,
                "verification_precision_proxy": verified,
                "readability_score_proxy": readability,
            }
        )

    metrics = {
        "sample_count": len(samples),
        "processed_count": sum(1 for r in rows if r.get("ok")),
        "step_transcription_quality": round(mean(transcription_scores), 4) if transcription_scores else 0.0,
        "algebra_consistency_rate": round(mean(consistency_scores), 4) if consistency_scores else 0.0,
        "verification_precision_proxy": round(mean(verified_flags), 4) if verified_flags else 0.0,
        "readability_score_proxy": round(mean(readability_scores), 4) if readability_scores else 0.0,
        "rows": rows,
    }
    (eval_dir / args.output).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
