from __future__ import annotations

from shared.interfaces.tracker_base import TrackerState
from server.core.tracking.track_manager import TrackManager
from server.core.tracking.tracker import Tracker


def test_tracker_state_transitions() -> None:
    tracker = Tracker()
    assert tracker.state == TrackerState.IDLE
    tracker.seed([[1]])
    assert tracker.state == TrackerState.SEEDED
    tracker.propagate(b"frame")
    assert tracker.state == TrackerState.TRACKING
    tracker.reset()
    assert tracker.state == TrackerState.IDLE


def test_track_manager_create_and_cleanup() -> None:
    manager = TrackManager(idle_timeout_seconds=0)
    manager.get_or_create("session-1")
    manager.cleanup_idle()
    manager.destroy("session-1")
