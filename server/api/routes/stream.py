from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shared.interfaces.pipeline_stage import PipelineContext

router = APIRouter()
_SESSION_LAST_SEEN: dict[str, float] = {}
_SESSION_TIMEOUT_SECONDS = 300.0


def _cleanup_expired_sessions(now: float) -> None:
    expired = [sid for sid, ts in _SESSION_LAST_SEEN.items() if now - ts > _SESSION_TIMEOUT_SECONDS]
    for sid in expired:
        _SESSION_LAST_SEEN.pop(sid, None)


def _fallback_stream_payload(session_id: str) -> dict[str, Any]:
    return {
        "request_id": str(uuid4()),
        "session_id": session_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_version": "stream-mock",
        "overlays": [],
        "warnings": ["streaming_pipeline_not_configured"],
    }


@router.websocket("/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id = websocket.query_params.get("session_id") or str(uuid4())
    _SESSION_LAST_SEEN[session_id] = time.time()
    try:
        while True:
            frame = await websocket.receive_bytes()
            now = time.time()
            _SESSION_LAST_SEEN[session_id] = now
            _cleanup_expired_sessions(now)

            pipeline = getattr(websocket.app.state, "streaming_pipeline", None)
            if pipeline is None:
                await websocket.send_json(_fallback_stream_payload(session_id))
                continue

            context = PipelineContext(image=frame, response={"session_id": session_id})
            result_ctx = pipeline.run(context, session_id=session_id)
            payload = result_ctx.response or _fallback_stream_payload(session_id)
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    finally:
        _SESSION_LAST_SEEN.pop(session_id, None)
