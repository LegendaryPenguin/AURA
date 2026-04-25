from __future__ import annotations

from server.utils.frame_buffer import CircularFrameBuffer


def test_push_overflow_drops_oldest_and_tracks_drop_count() -> None:
    buffer = CircularFrameBuffer[str](max_size=2)

    buffer.push("frame-1")
    buffer.push("frame-2")
    buffer.push("frame-3")

    assert len(buffer) == 2
    assert buffer.dropped_count == 1
    assert buffer.pop_oldest() == "frame-2"
    assert buffer.pop_oldest() == "frame-3"
    assert buffer.pop_oldest() is None


def test_snapshot_reports_size_drops_and_newest() -> None:
    buffer = CircularFrameBuffer[int](max_size=3)
    for frame in [10, 11, 12, 13]:
        buffer.push(frame)

    snapshot = buffer.snapshot()
    assert snapshot.size == 3
    assert snapshot.dropped_count == 1
    assert snapshot.newest == 13


def test_pop_newest_and_clear_behave_non_blocking() -> None:
    buffer = CircularFrameBuffer[int](max_size=2)

    assert buffer.pop_newest() is None

    buffer.push(1)
    buffer.push(2)
    assert buffer.pop_newest() == 2
    assert buffer.pop_newest() == 1
    assert buffer.pop_newest() is None

    buffer.push(3)
    buffer.clear()
    assert len(buffer) == 0
