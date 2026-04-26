from __future__ import annotations

from typing import Any


def _operation_hint(src: str, dst: str) -> tuple[str, str]:
    if src == dst:
        return "rewrite", "same expression rewritten for readability"
    if ("+" in src or "-" in src) and ("+" in dst or "-" in dst):
        return "balance_terms", "move or combine terms while preserving equality"
    if "/" in dst or dst.startswith("x=") or dst.startswith("-x="):
        return "isolate_variable", "divide both sides to isolate x"
    return "transform", "algebraic transformation"


def run_stage(normalized: dict[str, Any], verified: dict[str, Any]) -> dict[str, Any]:
    steps = [str(s) for s in normalized.get("normalized_steps", []) if str(s).strip()]
    transitions = verified.get("transitions", [])
    explanation_steps: list[dict[str, Any]] = []
    for tr in transitions:
        src = str(tr.get("from_step", ""))
        dst = str(tr.get("to_step", ""))
        op, reason = _operation_hint(src, dst)
        status = str(tr.get("status", "unknown"))
        if status == "inconsistent":
            reason = "transition changes equation meaning"
            op = "invalid_transform"
        elif status == "unknown":
            reason = "symbolic verifier could not confirm this step"
        explanation_steps.append(
            {
                "from_index": int(tr.get("from_index", 0)),
                "to_index": int(tr.get("to_index", 0)),
                "operation": op,
                "reason": reason,
                "validation": status,
                "token_diff": tr.get("token_diff", {"from_tokens": [], "to_tokens": []}),
            }
        )

    is_verified = bool(verified.get("is_verified", False))
    uncertainty = [str(r) for r in verified.get("uncertainty_reasons", [])]
    narration_intro = (
        "This solution is symbolically verified."
        if is_verified
        else "Draft walkthrough: some steps need review before final trust."
    )
    narration_outro = (
        "All transformations preserve the same solution."
        if is_verified
        else "Uncertainty reasons: " + ", ".join(uncertainty or ["unknown"])
    )

    readability = normalized.get("quality_scores", [])
    avg_readability = sum(float(v) for v in readability) / len(readability) if readability else 0.0
    render_quality_grade = "high" if avg_readability >= 0.78 else ("medium" if avg_readability >= 0.55 else "low")

    return {
        "stage": "narrate",
        "display_steps": steps,
        "explanation_steps": explanation_steps,
        "narration_intro": narration_intro,
        "narration_outro": narration_outro,
        "draft_mode": not is_verified,
        "render_quality_grade": render_quality_grade,
        "uncertainty_reasons": uncertainty,
        "visual_style": "hybrid",
        "phase_labels": [
            "Paper scan",
            "Handwriting diagnosis",
            "Side-by-side correction",
            "Verification lock-in",
        ],
    }
