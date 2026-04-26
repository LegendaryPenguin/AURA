from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

from normalize import normalize_step_text


@dataclass
class ParsedEquation:
    normalized: str
    parse_valid: bool


def parse_equation(step: str) -> ParsedEquation:
    s = normalize_step_text(step)
    return ParsedEquation(normalized=s, parse_valid="=" in s and "x" in s.lower())


def _tokenize_step(step: str) -> list[str]:
    return re.findall(r"\d+|[A-Za-z]+|==|!=|[=+\-*/()^]", step)


def _diff_tokens(src: str, dst: str) -> dict[str, list[str]]:
    src_tokens = _tokenize_step(src)
    dst_tokens = _tokenize_step(dst)
    changed_from: list[str] = []
    changed_to: list[str] = []
    max_len = max(len(src_tokens), len(dst_tokens))
    for i in range(max_len):
        s_tok = src_tokens[i] if i < len(src_tokens) else None
        d_tok = dst_tokens[i] if i < len(dst_tokens) else None
        if s_tok != d_tok:
            if s_tok is not None:
                changed_from.append(s_tok)
            if d_tok is not None:
                changed_to.append(d_tok)
    return {"from_tokens": changed_from, "to_tokens": changed_to}


def _sympy_equivalent(a: str, b: str) -> tuple[bool | None, str]:
    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import (
            implicit_multiplication_application,
            parse_expr,
            standard_transformations,
        )
    except Exception:
        return None, "sympy_unavailable"
    try:
        x = sp.symbols("x")
        lhs_a, rhs_a = a.split("=", 1)
        lhs_b, rhs_b = b.split("=", 1)
        transforms = standard_transformations + (implicit_multiplication_application,)
        eq_a = sp.Eq(parse_expr(lhs_a, transformations=transforms), parse_expr(rhs_a, transformations=transforms))
        eq_b = sp.Eq(parse_expr(lhs_b, transformations=transforms), parse_expr(rhs_b, transformations=transforms))
        sol_a = sp.solveset(eq_a, x, domain=sp.S.Reals)
        sol_b = sp.solveset(eq_b, x, domain=sp.S.Reals)
        eq = sp.simplify(sol_a.symmetric_difference(sol_b)) == sp.EmptySet
        return bool(eq), "ok"
    except Exception as exc:
        return None, f"sympy_parse_error: {exc}"


def _propose_correction(src: str, dst: str) -> tuple[str | None, str | None]:
    src_s = src.replace(" ", "")
    dst_s = dst.replace(" ", "")
    # Fix the common distribution error a(bx) -> kx where k != a*b.
    m = re.search(r"(\d+)\((\d+)x\)", src_s)
    if not m:
        return None, None
    target = int(m.group(1)) * int(m.group(2))
    kx_terms = re.findall(r"\d+x", dst_s)
    if not kx_terms:
        return None, None
    candidate = max(kx_terms, key=lambda t: int(t[:-1]))
    if int(candidate[:-1]) == target:
        return None, None
    corrected = dst_s.replace(candidate, f"{target}x", 1)
    explanation = f"{m.group(1)}*({m.group(2)}x) = {target}x, so {candidate} should be {target}x."
    return corrected, explanation


def final_substitution_check(step: str) -> dict[str, Any]:
    p = parse_equation(step)
    if not p.parse_valid:
        return {"status": "unknown", "reason": "not_parseable"}
    try:
        import sympy as sp
        from sympy.parsing.sympy_parser import (
            implicit_multiplication_application,
            parse_expr,
            standard_transformations,
        )
    except Exception:
        return {"status": "unknown", "reason": "sympy_unavailable"}
    try:
        lhs, rhs = p.normalized.split("=", 1)
        x = sp.symbols("x")
        transforms = standard_transformations + (implicit_multiplication_application,)
        lhs_expr = parse_expr(lhs, transformations=transforms)
        rhs_expr = parse_expr(rhs, transformations=transforms)
        solution = sp.solve(sp.Eq(lhs_expr, rhs_expr), x)
        if not solution:
            return {"status": "unknown", "reason": "no_solution_found"}
        solved_x = solution[0]
        lhs_value = sp.simplify(lhs_expr.subs(x, solved_x))
        rhs_value = sp.simplify(rhs_expr.subs(x, solved_x))
        ok = sp.simplify(lhs_value - rhs_value) == 0
        return {
            "status": "pass" if ok else "fail",
            "message": "LHS == RHS" if ok else "LHS != RHS",
            "lhs": str(lhs_value),
            "rhs": str(rhs_value),
            "x": str(solved_x),
        }
    except Exception as exc:
        return {"status": "unknown", "reason": f"sympy_check_error: {exc}"}


def run_stage(normalized: dict[str, Any]) -> dict[str, Any]:
    steps = [str(s) for s in normalized.get("normalized_steps", []) if str(s).strip()]
    transitions: list[dict[str, Any]] = []
    corrected_steps = list(steps)
    any_inconsistent = False
    any_unknown = False

    for idx in range(max(0, len(steps) - 1)):
        src = steps[idx]
        dst = steps[idx + 1]
        equivalent, reason = _sympy_equivalent(src, dst)
        if equivalent is True:
            status = "equivalent"
            correction_target = None
            correction_explanation = None
        elif equivalent is False:
            status = "inconsistent"
            any_inconsistent = True
            if reason == "ok":
                reason = "non_equivalent_solution_set"
            correction_target, correction_explanation = _propose_correction(src, dst)
            if correction_target:
                corrected_steps[idx + 1] = correction_target
        else:
            status = "unknown"
            any_unknown = True
            correction_target = None
            correction_explanation = None
        transitions.append(
            {
                "from_index": idx,
                "to_index": idx + 1,
                "from_step": src,
                "to_step": dst,
                "status": status,
                "reason": reason,
                "token_diff": _diff_tokens(src, dst),
                "correction_target": correction_target,
                "correction_explanation": correction_explanation,
            }
        )

    final_check = final_substitution_check(steps[-1]) if steps else {"status": "unknown", "reason": "no_steps"}
    verification_status = (
        "verified"
        if steps and not any_inconsistent and not any_unknown and final_check.get("status") == "pass"
        else "draft"
    )
    uncertainty_reasons: list[str] = []
    if any_inconsistent:
        uncertainty_reasons.append("inconsistent_transition_detected")
    if any_unknown:
        uncertainty_reasons.append("symbolic_verification_incomplete")
    if final_check.get("status") != "pass":
        uncertainty_reasons.append(f"final_check_{final_check.get('status', 'unknown')}")

    return {
        "stage": "verify",
        "transitions": transitions,
        "final_check": final_check,
        "verification_status": verification_status,
        "is_verified": verification_status == "verified",
        "uncertainty_reasons": uncertainty_reasons,
        "corrected_steps": corrected_steps,
    }
