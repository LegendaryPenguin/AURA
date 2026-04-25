from __future__ import annotations

import json

from server.utils.logger import log_event


def test_log_event_emits_json_with_required_fields(capsys) -> None:
    log_event(
        stage="analyze",
        result="ok",
        latency_ms=12.5,
        session_id="session-123",
        attempt=2,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert isinstance(payload["timestamp"], str)
    assert payload["stage"] == "analyze"
    assert payload["result"] == "ok"
    assert payload["latency_ms"] == 12.5
    assert payload["session_id"] == "session-123"
    assert payload["attempt"] == 2
