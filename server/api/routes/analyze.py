from __future__ import annotations

import asyncio
import base64
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from server.api.middleware.rate_limit import acquire_analyze_slot
from server.core.pipeline.snapshot_pipeline import PipelineTimeoutError
from shared.interfaces.pipeline_stage import PipelineContext

router = APIRouter()


def _decode_image_b64(image_b64: Any) -> bytes:
    if not isinstance(image_b64, str) or not image_b64.strip():
        raise ValueError("image (base64) must be a non-empty string")
    try:
        return base64.b64decode(image_b64, validate=True)
    except Exception as exc:
        raise ValueError("image is not valid base64 data") from exc


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _get_image_b64_from_form(image_b64: Any, form: Any) -> Any:
    if image_b64 is not None:
        return image_b64
    return form.get("image_base64") or form.get("image_b64")


def _get_audio_b64_from_form(form: Any) -> Any:
    return form.get("audio_base64") or form.get("audio_b64")


async def _extract_request_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()

        image_b64 = _get_image_b64_from_form(form.get("image_b64"), form)
        if image_b64 is None:
            image_upload = form.get("image") or form.get("image_file") or form.get("file")
            if image_upload is not None and hasattr(image_upload, "read"):
                image_bytes = await image_upload.read()
                image_b64 = base64.b64encode(image_bytes).decode("ascii")

        return {
            "image_b64": image_b64,
            "audio_b64": _get_audio_b64_from_form(form),
            "query": _as_text(form.get("query")),
            "request_id": _as_text(form.get("request_id")) or str(uuid4()),
            "session_id": _as_text(form.get("session_id")) or "local",
        }

    body = await request.json()
    if not isinstance(body, dict):
        raise ValueError("JSON request body must be an object")
    return {
        "image_b64": body.get("image_base64") or body.get("image_b64"),
        "audio_b64": body.get("audio_base64") or body.get("audio_b64"),
        "query": _as_text(body.get("query")),
        "request_id": _as_text(body.get("request_id")) or str(uuid4()),
        "session_id": _as_text(body.get("session_id")) or "local",
    }


async def _run_snapshot_pipeline(request: Request, context: PipelineContext) -> dict[str, Any]:
    pipeline = getattr(request.app.state, "snapshot_pipeline", None)
    if pipeline is None:
        now = datetime.now(UTC).isoformat()
        response = context.response or {}
        return {
            "request_id": str(response.get("request_id") or uuid4()),
            "session_id": str(response.get("session_id") or "local"),
            "created_at": now,
            "model_version": "mock",
            "overlays": [],
            "warnings": ["snapshot_pipeline_not_configured"],
        }

    session_id = (context.response or {}).get("session_id", "")
    if not isinstance(session_id, str):
        session_id = str(session_id)

    def _run_sync() -> PipelineContext:
        return pipeline.run(context, session_id=session_id)

    try:
        result = await asyncio.to_thread(_run_sync)
    except PipelineTimeoutError as exc:
        raise exc
    if result.response is None:
        raise ValueError("snapshot pipeline returned no response payload")
    return result.response


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

    text_query = _as_text(payload.get("query"))
    pipeline_ctx = PipelineContext(
        query=text_query,
        response={
            "image_base64": base64.b64encode(image_bytes).decode("ascii"),
            "audio_base64": payload.get("audio_b64"),
            "request_id": payload.get("request_id", str(uuid4())),
            "session_id": payload.get("session_id", "local"),
        },
    )

    try:
        async with acquire_analyze_slot():
            try:
                result = await _run_snapshot_pipeline(request, pipeline_ctx)
            except PipelineTimeoutError as exc:
                return JSONResponse(
                    status_code=408,
                    content={"error": str(exc), "code": 408, "stage": "pipeline"},
                )
            except Exception as exc:
                return JSONResponse(
                    status_code=500,
                    content={"error": str(exc), "code": 500, "stage": "pipeline"},
                )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail), "code": exc.status_code}
        return JSONResponse(status_code=exc.status_code, content=detail)

    return JSONResponse(status_code=200, content=result)
