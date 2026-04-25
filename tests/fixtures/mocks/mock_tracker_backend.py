from __future__ import annotations

from typing import Any

from shared.interfaces.tracker_base import TrackerBackend, TrackerState


class MockTrackerBackend(TrackerBackend):
    def __init__(self) -> None:
        self._state = TrackerState.IDLE
        self._mask: Any = None

    @property
    def state(self) -> TrackerState:
        return self._state

    def seed(self, mask: Any) -> None:
        self._mask = mask
        self._state = TrackerState.SEEDED

    def propagate(self, frame: bytes) -> Any:
        if self._mask is None:
            self._state = TrackerState.LOST
            return None
        self._state = TrackerState.TRACKING
        return {"frame_len": len(frame), "mask": self._mask}

    def reset(self) -> None:
        self._mask = None
        self._state = TrackerState.IDLE
