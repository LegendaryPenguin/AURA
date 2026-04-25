from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import pytesseract


@dataclass
class StepExtraction:
    steps: list[str]
    confidences: list[float]
    avg_conf: float
    notes: list[str]


@dataclass
class ParsedEquation:
    normalized: str
    coeff_x: float | None
    constant: float | None
    rhs: float | None
    parse_valid: bool


def _load_image(image_path: Path) -> Any:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not read image at: {image_path}")
    return image


def _line_boxes(gray: Any) -> list[tuple[int, int]]:
    inv = cv2.bitwise_not(gray)
    _, bw = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    proj = (bw > 0).sum(axis=1)
    thresh = max(6, int(0.02 * bw.shape[1]))
    active = proj > thresh
    bands: list[tuple[int, int]] = []
    start = None
    for y, on in enumerate(active):
        if on and start is None:
            start = y
        elif not on and start is not None:
            if y - start >= 10:
                bands.append((max(0, start - 4), min(bw.shape[0], y + 4)))
            start = None
    if start is not None and bw.shape[0] - start >= 10:
        bands.append((max(0, start - 4), bw.shape[0]))
    return bands


def _normalize_step_text(text: str) -> str:
    s = text.strip().replace(" ", "")
    s = s.replace("|", "1").replace("O", "0").replace("X", "x")
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"([0-9])\(", r"\1*(", s)
    s = re.sub(r"\)([0-9a-zA-Z])", r")*\1", s)
    return s


def _step_quality_score(step: str) -> float:
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


def extract_steps(image_path: Path, tesseract_cmd: str | None = None) -> StepExtraction:
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    image = _load_image(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    steps: list[str] = []
    confs: list[float] = []
    notes: list[str] = []
    for y0, y1 in _line_boxes(gray):
        crop = gray[y0:y1, :]
        data = pytesseract.image_to_data(
            crop,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+-=*/()[]{}^., ",
        )
        tokens: list[str] = []
        local: list[float] = []
        for i, token in enumerate(data["text"]):
            tk = token.strip()
            if not tk:
                continue
            tokens.append(tk)
            try:
                c = float(data["conf"][i])
            except ValueError:
                c = 0.0
            if c > 0:
                local.append(c / 100.0)
        line = _normalize_step_text(" ".join(tokens))
        if not line:
            continue
        if _step_quality_score(line) < 0.35:
            notes.append(f"Hidden noisy OCR line: {line}")
            continue
        steps.append(line)
        confs.append(sum(local) / len(local) if local else 0.0)
    avg = sum(confs) / len(confs) if confs else 0.0
    return StepExtraction(steps=steps, confidences=confs, avg_conf=avg, notes=notes)


def _safe_eval(expr: str) -> float | None:
    if not re.fullmatch(r"[0-9\.\+\-\*\/\(\)\s]+", expr):
        return None
    try:
        node = ast.parse(expr, mode="eval")
        value = eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, {})
    except Exception:
        return None
    return float(value) if isinstance(value, (int, float)) else None


def _parse_linear_equation(step: str) -> ParsedEquation:
    s = _normalize_step_text(step)
    if "=" not in s:
        return ParsedEquation(s, None, None, None, False)
    lhs, rhs = s.split("=", 1)
    rhs_val = _safe_eval(rhs)
    if rhs_val is None:
        return ParsedEquation(s, None, None, None, False)
    cleaned = lhs.replace("-", "+-")
    terms = [t for t in cleaned.split("+") if t]
    coeff = 0.0
    constant = 0.0
    seen_x = False
    for term in terms:
        if "x" in term:
            seen_x = True
            part = term.replace("x", "")
            if part in ("", "+"):
                coeff += 1.0
            elif part == "-":
                coeff -= 1.0
            else:
                try:
                    coeff += float(part)
                except ValueError:
                    return ParsedEquation(s, None, None, rhs_val, False)
        else:
            try:
                constant += float(term)
            except ValueError:
                return ParsedEquation(s, None, None, rhs_val, False)
    if not seen_x:
        return ParsedEquation(s, None, None, rhs_val, False)
    return ParsedEquation(s, coeff, constant, rhs_val, True)


def _format_num(v: float) -> str:
    return str(int(round(v))) if abs(v - round(v)) < 1e-9 else f"{v:.6g}"


def _canonicalize(step: str) -> str:
    p = _parse_linear_equation(step)
    if not p.parse_valid or p.coeff_x is None or p.constant is None or p.rhs is None:
        return _normalize_step_text(step)
    coeff = p.coeff_x
    lhs = "x" if abs(coeff - 1.0) < 1e-9 else ("-x" if abs(coeff + 1.0) < 1e-9 else f"{_format_num(coeff)}x")
    if abs(p.constant) > 1e-9:
        lhs += f"+{_format_num(p.constant)}" if p.constant > 0 else f"-{_format_num(abs(p.constant))}"
    return f"{lhs}={_format_num(p.rhs)}"


def _derive_explanations(display_steps: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    explanations: list[dict[str, Any]] = []
    flags: list[str] = []
    parsed = [_parse_linear_equation(s) for s in display_steps]
    for i in range(max(0, len(display_steps) - 1)):
        op = "rewrite"
        reason = "simplify expression"
        valid = "uncertain"
        a = parsed[i]
        b = parsed[i + 1]
        if a.parse_valid and b.parse_valid and a.coeff_x is not None and a.constant is not None and a.rhs is not None and b.coeff_x is not None and b.constant is not None and b.rhs is not None:
            sa = (a.rhs - a.constant) / a.coeff_x if abs(a.coeff_x) > 1e-9 else None
            sb = (b.rhs - b.constant) / b.coeff_x if abs(b.coeff_x) > 1e-9 else None
            if sa is not None and sb is not None and abs(sa - sb) <= 1e-6:
                valid = "equivalent"
                if abs(a.constant - b.constant) > 1e-9:
                    delta = a.constant - b.constant
                    op = f"subtract {_format_num(delta)} both sides" if delta > 0 else f"add {_format_num(abs(delta))} both sides"
                    reason = "preserve equality while isolating x"
                elif abs(a.coeff_x - b.coeff_x) > 1e-9:
                    op = "combine like terms"
                    reason = "simplify left side"
            else:
                valid = "inconsistent"
                op = "invalid transform"
                reason = "changes implied solution"
        explanations.append(
            {
                "from_index": i,
                "to_index": i + 1,
                "operation": op,
                "reason": reason,
                "validation": valid,
            }
        )
        flags.append(valid)
    return explanations, flags


def _final_check(step: str) -> dict[str, Any]:
    p = _parse_linear_equation(step)
    if not p.parse_valid or p.coeff_x is None or p.constant is None or p.rhs is None or abs(p.coeff_x) < 1e-9:
        return {"status": "unknown", "lhs": "", "rhs": "", "message": "Final line not parseable"}
    x = (p.rhs - p.constant) / p.coeff_x
    lhs = p.coeff_x * x + p.constant
    ok = abs(lhs - p.rhs) <= 1e-6
    return {"status": "pass" if ok else "fail", "lhs": _format_num(lhs), "rhs": _format_num(p.rhs), "message": "LHS == RHS" if ok else "LHS != RHS"}


def build_tutor_story(steps: list[str]) -> dict[str, Any]:
    original_steps = [s for s in steps if s]
    display_steps = [_canonicalize(s) for s in original_steps]
    hidden_noisy_steps: list[str] = []
    readability = [_step_quality_score(s) for s in display_steps]
    grade = "high" if readability and sum(readability) / len(readability) >= 0.78 else ("medium" if readability and sum(readability) / len(readability) >= 0.55 else "low")
    explanations, flags = _derive_explanations(display_steps)
    final = _final_check(display_steps[-1]) if display_steps else {"status": "unknown", "lhs": "", "rhs": "", "message": "No final step"}
    draft_mode = final.get("status") != "pass"
    return {
        "original_steps": original_steps,
        "display_steps": display_steps,
        "normalized_steps": display_steps,
        "corrected_steps": display_steps,
        "hidden_noisy_steps": hidden_noisy_steps,
        "step_readability_scores": readability,
        "render_quality_grade": grade,
        "explanation_steps": explanations,
        "validation_flags": flags,
        "final_check": final,
        "draft_mode": draft_mode,
    }
