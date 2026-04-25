from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Generic, TypeVar


FrameT = TypeVar("FrameT")


@dataclass(frozen=True)
class BufferSnapshot(Generic[FrameT]):
    size: int
    dropped_count: int
    newest: FrameT | None


class CircularFrameBuffer(Generic[FrameT]):
    """A bounded, non-blocking buffer that drops oldest frames on overflow."""

    def __init__(self, max_size: int) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be > 0")
        self._max_size = max_size
        self._frames: Deque[FrameT] = deque(maxlen=max_size)
        self._dropped_count = 0

    @property
    def max_size(self) -> int:
        return self._max_size

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    def push(self, frame: FrameT) -> None:
        if len(self._frames) == self._max_size:
            self._dropped_count += 1
        self._frames.append(frame)

    def pop_oldest(self) -> FrameT | None:
        if not self._frames:
            return None
        return self._frames.popleft()

    def pop_newest(self) -> FrameT | None:
        if not self._frames:
            return None
        return self._frames.pop()

    def snapshot(self) -> BufferSnapshot[FrameT]:
        newest = self._frames[-1] if self._frames else None
        return BufferSnapshot(size=len(self._frames), dropped_count=self._dropped_count, newest=newest)

    def clear(self) -> None:
        self._frames.clear()

    def __len__(self) -> int:
        return len(self._frames)
