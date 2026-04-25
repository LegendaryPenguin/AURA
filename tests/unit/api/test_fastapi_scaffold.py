"""WS3-A: FastAPI app wiring (routes mounted, health reachable)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.main import create_app


def test_get_root_404() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/")
    assert response.status_code == 404


def test_openapi_includes_routes() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})
    assert "/health" in paths
    assert "/analyze" in paths


def test_get_health_json() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "models" in data
