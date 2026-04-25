from __future__ import annotations

import base64
import inspect
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from server.api.middleware.rate_limit import acquire_analyze_slot

router = APIRouter()


def _decode_image_b64(image_b64: Any) -> bytes:
    if not isinstance(image_b64, str) or not image_b64.strip():
        raise ValueError("image_b64 must be a non-empty base64 string")
    try:
        return base64.b64decode(image_b64, validate=True)
    except Exception as exc:
        raise ValueError("image_b64 is not valid base64 data") from exc


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


async def _extract_request_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()

        image_b64 = form.get("image_b64")
        if image_b64 is None:
            image_upload = form.get("image") or form.get("image_file") or form.get("file")
            if image_upload is not None and hasattr(image_upload, "read"):
                image_bytes = await image_upload.read()
                image_b64 = base64.b64encode(image_bytes).decode("ascii")

        return {
            "image_b64": image_b64,
            "audio_b64": form.get("audio_b64"),
            "query": _as_text(form.get("query")),
        }

    body = await request.json()
    if not isinstance(body, dict):
        raise ValueError("JSON request body must be an object")
    return {
        "image_b64": body.get("image_b64"),
        "audio_b64": body.get("audio_b64"),
        "query": _as_text(body.get("query")),
    }


async def _run_snapshot_pipeline(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    pipeline = getattr(request.app.state, "snapshot_pipeline", None)
    if pipeline is None:
        now = datetime.now(UTC).isoformat()
        return {
            "request_id": str(uuid4()),
            "session_id": "local",
            "created_at": now,
            "model_version": "mock",
            "overlays": [],
            "warnings": ["snapshot_pipeline_not_configured"],
        }

    result = pipeline(payload)
    if inspect.isawaitable(result):
        result = await result
    if not isinstance(result, dict):
        raise ValueError("snapshot pipeline returned an invalid response")
    return result


@router.post("/analyze")
async def analyze(request: Request) -> JSONResponse:
    try:
        payload = await _extract_request_payload(request)
        image_bytes = _decode_image_b64(payload.get("image_b64"))
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": str(exc), "code": 422, "stage": "validation"},
        )
    except Exception:
        return JSONResponse(
            status_code=422,
            content={"error": "invalid request payload", "code": 422, "stage": "validation"},
        )

    pipeline_payload = {
        "image_b64": base64.b64encode(image_bytes).decode("ascii"),
        "audio_b64": payload.get("audio_b64"),
        "query": payload.get("query"),
    }

    try:
        async with acquire_analyze_slot():
            try:
                result = await _run_snapshot_pipeline(request, pipeline_payload)
            except Exception as exc:
                return JSONResponse(
                    status_code=500,
                    content={"error": str(exc), "code": 500, "stage": "pipeline"},
                )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail), "code": exc.status_code}
        return JSONResponse(status_code=exc.status_code, content=detail)

    return JSONResponse(status_code=200, content=result)
