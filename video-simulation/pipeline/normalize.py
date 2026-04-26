from __future__ import annotations

import re
from typing import Any


def step_quality_score(step: str) -> float:
    score = 0.0
    if "=" in step:
        score += 0.45
    if re.search(r"[0-9]", step):
        score += 0.2
    if "x" in step.lower():
        score += 0.2
    if re.search(r"[\+\-\*/]", step):
        score += 0.15
    if re.search(r"[A-Za-z]{4,}", step):
        score -= 0.25
    return max(0.0, min(1.0, score))


def normalize_step_text(text: str) -> str:
    s = text.strip().replace(" ", "")
    s = s.replace("|", "1").replace("O", "0").replace("X", "x")
    s = s.replace("—", "-").replace("–", "-")
    # Keep implicit multiplication style for display fidelity (e.g. 4(2x)).
    return s


def run_stage(vision_parse: dict[str, Any], min_quality: float = 0.35) -> dict[str, Any]:
    raw_lines = vision_parse.get("lines", [])
    normalized_steps: list[str] = []
    dropped_steps: list[dict[str, Any]] = []
    per_step_quality: list[float] = []

    for item in raw_lines:
        text = normalize_step_text(str(item.get("text", "")))
        if not text:
            continue
        quality = step_quality_score(text)
        per_step_quality.append(quality)
        if quality >= min_quality:
            normalized_steps.append(text)
        else:
            dropped_steps.append({"text": text, "quality": round(quality, 4), "reason": "low_quality"})

    return {
        "stage": "normalize",
        "normalized_steps": normalized_steps,
        "dropped_steps": dropped_steps,
        "quality_scores": [round(v, 4) for v in per_step_quality],
        "avg_quality": round(sum(per_step_quality) / len(per_step_quality), 4) if per_step_quality else 0.0,
    }
