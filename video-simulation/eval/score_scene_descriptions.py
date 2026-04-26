from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _score_text(text: str, expected: list[str], forbidden: list[str]) -> float:
    lowered = text.lower()
    exp_hits = sum(1 for token in expected if token.lower() in lowered)
    forbid_hits = sum(1 for token in forbidden if token.lower() in lowered)
    expected_score = exp_hits / max(1, len(expected))
    penalty = min(1.0, forbid_hits / max(1, len(forbidden))) if forbidden else 0.0
    return max(0.0, expected_score - (0.5 * penalty))


def _collect_story_text(artifact: dict[str, Any]) -> str:
    narrate = artifact.get("narrate", {})
    chunks = [
        str(narrate.get("narration_intro", "")),
        " ".join(str(x) for x in narrate.get("explanation_steps", [])),
        str(narrate.get("narration_outro", "")),
    ]
    return " ".join(chunks).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Score scene description quality from pipeline artifacts.")
    parser.add_argument("--artifact", required=True, help="Path to ocr_result_*.json artifact")
    parser.add_argument(
        "--fixtures",
        default=str(Path(__file__).with_name("scene_description_fixtures.json")),
        help="Path to scoring fixture json",
    )
    parser.add_argument("--output", default="scene_description_score.json")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    artifact = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    fixture_payload = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
    cases = fixture_payload.get("cases", [])
    text = _collect_story_text(artifact)

    rows: list[dict[str, Any]] = []
    for case in cases:
        score = _score_text(
            text=text,
            expected=list(case.get("expected_keywords", [])),
            forbidden=list(case.get("forbidden_keywords", [])),
        )
        min_score = float(case.get("min_score", 0.6))
        rows.append(
            {
                "id": case.get("id"),
                "score": round(score, 4),
                "min_score": min_score,
                "pass": score >= min_score,
            }
        )

    final_score = sum(float(r["score"]) for r in rows) / max(1, len(rows))
    result = {
        "artifact": args.artifact,
        "scene_description_score": round(final_score, 4),
        "rows": rows,
        "pass": all(bool(r["pass"]) for r in rows),
    }
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if args.enforce and not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
