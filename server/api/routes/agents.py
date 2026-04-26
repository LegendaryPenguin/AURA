from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/agents/trigger")
async def trigger_agent(payload: dict[str, Any]) -> JSONResponse:
    component = str(payload.get("component") or payload.get("component_id") or "").strip()
    if not component:
        return JSONResponse(
            status_code=422,
            content={"error": "component is required", "code": 422, "stage": "agents"},
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "queued",
            "component": component,
            "message": "agent subsystem not loaded; returned mock dispatch",
        },
    )
