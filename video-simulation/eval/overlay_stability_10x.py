from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from statistics import mean
from typing import Any


def _run_once(
    *,
    root: Path,
    image: Path,
    manual_steps: Path,
    style: str,
    preview: bool,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(root / "pipeline" / "run_pipeline.py"),
        "--image",
        str(image),
        "--manual-steps",
        str(manual_steps),
        "--style",
        style,
    ]
    if preview:
        cmd.append("--preview")
    result = subprocess.run(cmd, cwd=str(root / "pipeline"), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr.strip() or result.stdout.strip()}

    stage_match = re.search(r"Stage artifacts:\s*(.+)", result.stdout)
    video_match = re.search(r"Video file:\s*(.+)", result.stdout)
    if not stage_match:
        return {"ok": False, "error": "missing_stage_artifacts_path", "stdout": result.stdout}
    stage_dir = Path(stage_match.group(1).strip())
    render_path = stage_dir / "render.json"
    if not render_path.exists():
        return {"ok": False, "error": "missing_render_json", "stage_dir": str(stage_dir)}
    render_payload = json.loads(render_path.read_text(encoding="utf-8"))
    qa = render_payload.get("qa_report", {})
    return {
        "ok": True,
        "stage_dir": str(stage_dir),
        "video_file": video_match.group(1).strip() if video_match else "",
        "qa_report": qa,
    }


def _bbox_drift(reference: list[int], current: list[int]) -> float:
    if len(reference) != 4 or len(current) != 4:
        return 0.0
    return float(sum(abs(int(a) - int(b)) for a, b in zip(reference, current)) / 4.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 10x overlay stability check for in-place snapping.")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--manual-steps", required=True, help="Manual steps JSON path")
    parser.add_argument("--iterations", type=int, default=10, help="Number of repeated runs")
    parser.add_argument("--style", default="paper_3b1b", help="Render style")
    parser.add_argument("--preview", action="store_true", help="Use preview timing")
    parser.add_argument("--output", default="overlay_stability_10x.json", help="Output report filename in eval/")
    args = parser.parse_args()

    eval_dir = Path(__file__).resolve().parent
    root = eval_dir.parent
    image = (root / args.image).resolve() if not Path(args.image).is_absolute() else Path(args.image)
    manual_steps = (root / args.manual_steps).resolve() if not Path(args.manual_steps).is_absolute() else Path(args.manual_steps)

    rows: list[dict[str, Any]] = []
    for i in range(args.iterations):
        run = _run_once(root=root, image=image, manual_steps=manual_steps, style=args.style, preview=args.preview)
        run["iteration"] = i + 1
        rows.append(run)

    ok_rows = [r for r in rows if r.get("ok")]
    ref_bbox: list[int] | None = None
    drifts: list[float] = []
    qa_pass_rates: list[float] = []
    for row in ok_rows:
        qa = row.get("qa_report", {})
        qa_pass_rates.append(1.0 if qa.get("passed") else 0.0)
        bbox = qa.get("transform_meta", {}).get("source_bbox", [])
        if isinstance(bbox, list) and len(bbox) == 4:
            if ref_bbox is None:
                ref_bbox = [int(v) for v in bbox]
            else:
                drifts.append(_bbox_drift(ref_bbox, [int(v) for v in bbox]))

    report = {
        "iterations": args.iterations,
        "ok_runs": len(ok_rows),
        "failed_runs": len(rows) - len(ok_rows),
        "qa_pass_rate": round(mean(qa_pass_rates), 4) if qa_pass_rates else 0.0,
        "mean_source_bbox_drift_px": round(mean(drifts), 4) if drifts else 0.0,
        "max_source_bbox_drift_px": round(max(drifts), 4) if drifts else 0.0,
        "rows": rows,
    }
    out_path = eval_dir / args.output
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
