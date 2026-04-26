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


def _normalize_math_text(s: str) -> str:
    s = s.replace(" ", "")
    s = s.replace("*x", "x")
    s = s.replace("+-", "-")
    s = s.replace("--", "+")
    return s


def _derive_corrected_steps(steps: list[str], explanation_steps: list[dict[str, Any]]) -> list[str]:
    corrected = list(steps)
    if not steps:
        return corrected
    # Seed direct correction targets first.
    for tr in explanation_steps:
        tgt = tr.get("correction_target")
        to_i = int(tr.get("to_index", -1))
        if isinstance(tgt, str) and tgt.strip() and 0 <= to_i < len(corrected):
            corrected[to_i] = _normalize_math_text(tgt)

    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import (
            implicit_multiplication_application,
            parse_expr,
            standard_transformations,
        )
    except Exception:
        return corrected

    x = sp.symbols("x")
    transforms = standard_transformations + (implicit_multiplication_application,)

    def parse_eq(eq: str) -> tuple[Any, Any] | None:
        if "=" not in eq:
            return None
        l, r = eq.split("=", 1)
        try:
            return parse_expr(l, transformations=transforms), parse_expr(r, transformations=transforms)
        except Exception:
            return None

    def fmt_expr(e: Any) -> str:
        txt = str(sp.simplify(e))
        txt = txt.replace("**", "^")
        txt = txt.replace("*x", "x")
        txt = txt.replace(" ", "")
        return txt

    for tr in explanation_steps:
        to_i = int(tr.get("to_index", -1))
        frm_i = int(tr.get("from_index", -1))
        if not (0 <= frm_i < len(corrected) and 0 <= to_i < len(corrected)):
            continue
        if str(tr.get("validation", "unknown")) == "inconsistent":
            continue
        # If already explicitly corrected, keep it.
        if tr.get("correction_target"):
            continue
        parsed = parse_eq(corrected[frm_i])
        if parsed is None:
            continue
        lhs, rhs = parsed
        op = str(tr.get("operation", "transform"))
        try:
            if op == "balance_terms":
                # Combine terms on LHS while preserving RHS.
                new_lhs = sp.expand(lhs)
                corrected[to_i] = _normalize_math_text(f"{fmt_expr(new_lhs)}={fmt_expr(rhs)}")
            elif op == "transform":
                # Move constant term from LHS to RHS for linear expression ax + b.
                a = sp.expand(lhs).coeff(x)
                b = sp.expand(lhs).subs(x, 0)
                new_lhs = a * x
                new_rhs = sp.simplify(rhs - b)
                corrected[to_i] = _normalize_math_text(f"{fmt_expr(new_lhs)}={fmt_expr(new_rhs)}")
            elif op == "isolate_variable":
                a = sp.expand(lhs).coeff(x)
                if a != 0:
                    new_rhs = sp.simplify(rhs / a)
                    corrected[to_i] = _normalize_math_text(f"x={fmt_expr(new_rhs)}")
        except Exception:
            continue
    return corrected


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
                "correction_target": tr.get("correction_target"),
                "correction_explanation": tr.get("correction_explanation"),
            }
        )
    corrected_steps = _derive_corrected_steps(steps, explanation_steps)

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
        "corrected_steps": corrected_steps,
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
