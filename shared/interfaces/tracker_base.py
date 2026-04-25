from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class TrackerState(Enum):
    IDLE = "idle"
    SEEDED = "seeded"
    TRACKING = "tracking"
    LOST = "lost"


class TrackerBackend(ABC):
    @property
    @abstractmethod
    def state(self) -> TrackerState:
        """Return current tracker lifecycle state."""

    @abstractmethod
    def seed(self, mask: Any) -> None:
        """Initialize tracker from a seed mask."""

    @abstractmethod
    def propagate(self, frame: bytes) -> Any:
        """Propagate mask to the next frame."""

    @abstractmethod
    def reset(self) -> None:
        """Clear tracker state."""
