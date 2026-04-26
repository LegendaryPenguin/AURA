from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any

def _normalize_step_text(text: str) -> str:
    s = text.strip().replace(" ", "")
    s = s.replace("|", "1").replace("O", "0").replace("X", "x")
    s = s.replace("—", "-").replace("–", "-")
    return s


def _extract_json_object(raw_content: Any) -> dict[str, Any]:
    if isinstance(raw_content, dict):
        return raw_content
    if isinstance(raw_content, list):
        text_parts = []
        for part in raw_content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        raw_text = "\n".join(text_parts)
    else:
        raw_text = str(raw_content or "")
    candidate = raw_text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for start in (m.start() for m in re.finditer(r"\{", candidate)):
        try:
            parsed, _ = decoder.raw_decode(candidate[start:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise ValueError("VLM response did not include parseable JSON object")


def _endpoint_from_repo_config() -> str:
    config_path = Path(__file__).resolve().parents[2] / "config" / "models.yaml"
    if not config_path.exists():
        return ""
    text = config_path.read_text(encoding="utf-8")
    in_vlm = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"^[A-Za-z_]+\s*:\s*$", line):
            in_vlm = line.startswith("vlm:")
            continue
        if in_vlm and line.startswith("endpoint:"):
            value = line.split(":", 1)[1].strip().strip('"').strip("'")
            return value
    return ""


def _qwen_vl_extract_lines(image_path: Path) -> dict[str, Any]:
    endpoint = os.getenv("VIDEO_SIM_VLM_ENDPOINT", "").rstrip("/") or _endpoint_from_repo_config().rstrip("/")
    model_id = os.getenv("VIDEO_SIM_VLM_MODEL_ID", "Qwen/Qwen2.5-VL-7B-Instruct")
    if not endpoint:
        return {
            "lines": [],
            "notes": ["VIDEO_SIM_VLM_ENDPOINT not set and config endpoint unavailable"],
            "model": "unavailable",
            "error_code": "vlm_endpoint_missing",
        }

    try:
        import httpx
    except Exception:
        return {
            "lines": [],
            "notes": ["httpx unavailable for VLM stage"],
            "model": "unavailable",
            "error_code": "vlm_client_missing",
        }

    image_bytes = image_path.read_bytes()
    data_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
    system_prompt = (
        "Extract handwritten algebra lines in reading order. Return strict JSON object: "
        '{"lines":[{"text":"...","confidence":0.0}],"notes":[string]}. '
        "No markdown."
    )

    payload = {
        "model": model_id,
        "temperature": 0,
        "max_tokens": 512,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all equation steps exactly."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(f"{endpoint}/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = _extract_json_object(content)
        raw_lines = parsed.get("lines", []) if isinstance(parsed, dict) else []
        lines = []
        for item in raw_lines:
            if not isinstance(item, dict):
                continue
            txt = _normalize_step_text(str(item.get("text", "")).strip())
            if not txt:
                continue
            lines.append(
                {
                    "text": txt,
                    "confidence": float(item.get("confidence", 0.0)),
                    "source": "vlm",
                }
            )
        notes = [str(n) for n in parsed.get("notes", [])] if isinstance(parsed, dict) else []
        return {"lines": lines, "notes": notes, "model": model_id}
    except Exception as exc:
        return {
            "lines": [],
            "notes": [f"VLM extraction failed: {exc}"],
            "model": model_id,
            "error_code": "vlm_request_failed",
        }


def run_stage(image_path: Path) -> dict[str, Any]:
    strict_mode = os.getenv("VIDEO_SIM_STRICT_MODE", "0") == "1"
    vlm_result = _qwen_vl_extract_lines(image_path)
    lines = vlm_result.get("lines", [])
    avg_confidence = sum(float(x.get("confidence", 0.0)) for x in lines) / len(lines) if lines else 0.0
    parse_status = "ok" if lines else "error"
    parser = "qwen2.5-vl" if lines else "none"
    error_code = vlm_result.get("error_code")
    if strict_mode and parse_status != "ok":
        notes = list(vlm_result.get("notes", []))
        notes.append("strict_mode_parse_failure")
        return {
            "stage": "vision_parse",
            "parser": "none",
            "model": vlm_result.get("model", "unavailable"),
            "lines": [],
            "avg_confidence": 0.0,
            "notes": notes,
            "parse_status": "error",
            "error_code": error_code or "strict_mode_parse_failure",
        }
    return {
        "stage": "vision_parse",
        "parser": parser,
        "model": vlm_result.get("model", "unavailable"),
        "lines": lines,
        "avg_confidence": round(avg_confidence, 4),
        "notes": vlm_result.get("notes", []),
        "parse_status": parse_status,
        "error_code": error_code,
    }
