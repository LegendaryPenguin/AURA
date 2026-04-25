from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any


def log_event(stage: str, result: str, latency_ms: float, session_id: str, **extra: Any) -> None:
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "result": result,
        "latency_ms": float(latency_ms),
        "session_id": session_id,
    }
    payload.update(extra)
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()
