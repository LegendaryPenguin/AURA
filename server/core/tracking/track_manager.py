from __future__ import annotations

import time

from server.core.tracking.tracker import Tracker


class TrackManager:
    def __init__(self, idle_timeout_seconds: float = 300.0) -> None:
        self._idle_timeout_seconds = idle_timeout_seconds
        self._trackers: dict[str, Tracker] = {}
        self._last_seen: dict[str, float] = {}

    def get_or_create(self, session_id: str) -> Tracker:
        tracker = self._trackers.get(session_id)
        if tracker is None:
            tracker = Tracker()
            self._trackers[session_id] = tracker
        self._last_seen[session_id] = time.monotonic()
        return tracker

    def destroy(self, session_id: str) -> None:
        tracker = self._trackers.pop(session_id, None)
        if tracker is not None:
            tracker.reset()
        self._last_seen.pop(session_id, None)

    def cleanup_idle(self) -> None:
        now = time.monotonic()
        for session_id, ts in list(self._last_seen.items()):
            if now - ts > self._idle_timeout_seconds:
                self.destroy(session_id)
