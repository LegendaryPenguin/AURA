from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api.routes import api_router
from shared.interfaces.pipeline_stage import PipelineContext


class _MockStreamingPipeline:
    def run(self, context: PipelineContext, session_id: str = "") -> PipelineContext:
        context.response = {
            "request_id": "stream-1",
            "session_id": session_id or "session-x",
            "overlays": [],
        }
        return context


def test_stream_route_round_trip() -> None:
    app = FastAPI()
    app.include_router(api_router)
    app.state.streaming_pipeline = _MockStreamingPipeline()
    with TestClient(app) as client:
        with client.websocket_connect("/stream?session_id=sess-1") as websocket:
            websocket.send_bytes(b"frame")
            data = websocket.receive_json()
    assert data["session_id"] == "sess-1"
    assert "overlays" in data


def test_agents_trigger_mock_response() -> None:
    app = FastAPI()
    app.include_router(api_router)
    with TestClient(app) as client:
        response = client.post("/agents/trigger", json={"component": "planner"})
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
