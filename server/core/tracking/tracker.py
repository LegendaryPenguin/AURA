from __future__ import annotations

import time
from typing import Any

from shared.interfaces.tracker_base import TrackerBackend, TrackerState


class Tracker(TrackerBackend):
    def __init__(self, lost_timeout_seconds: float = 10.0) -> None:
        self._state = TrackerState.IDLE
        self._last_mask: Any = None
        self._lost_since: float | None = None
        self._lost_timeout_seconds = lost_timeout_seconds

    @property
    def state(self) -> TrackerState:
        if self._state == TrackerState.LOST and self._lost_since is not None:
            if (time.monotonic() - self._lost_since) > self._lost_timeout_seconds:
                self.reset()
        return self._state

    def seed(self, mask: Any) -> None:
        self._last_mask = mask
        self._state = TrackerState.SEEDED
        self._lost_since = None

    def propagate(self, frame: bytes) -> Any:
        if self._state in {TrackerState.IDLE, TrackerState.LOST}:
            return None
        if not frame:
            self._state = TrackerState.LOST
            self._lost_since = time.monotonic()
            return None
        self._state = TrackerState.TRACKING
        return self._last_mask

    def reset(self) -> None:
        self._state = TrackerState.IDLE
        self._last_mask = None
        self._lost_since = None
