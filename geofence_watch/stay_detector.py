"""Detects when an object stays within a fence for a minimum duration."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

from .event import EventType, GeofenceEvent


@dataclass
class StayResult:
    object_id: str
    fence_name: str
    duration_seconds: float
    entered_at: float

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"StayResult(object_id={self.object_id!r}, "
            f"fence_name={self.fence_name!r}, "
            f"duration_seconds={self.duration_seconds:.2f})"
        )


class StayDetector:
    """Fires a callback when an object remains inside a fence longer than
    *min_seconds*."""

    def __init__(
        self,
        min_seconds: float = 60.0,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if min_seconds <= 0:
            raise ValueError("min_seconds must be positive")
        self._min_seconds = min_seconds
        self._clock = clock
        # (object_id, fence_name) -> entered_at timestamp
        self._entries: Dict[Tuple[str, str], float] = {}
        self._callbacks: Dict[str, Callable[[StayResult], None]] = {}

    @property
    def min_seconds(self) -> float:
        return self._min_seconds

    @property
    def callback_names(self) -> Tuple[str, ...]:
        return tuple(self._callbacks)

    def add_callback(self, name: str, fn: Callable[[StayResult], None]) -> None:
        if not callable(fn):
            raise TypeError("fn must be callable")
        self._callbacks[name] = fn

    def remove_callback(self, name: str) -> None:
        self._callbacks.pop(name, None)

    def ingest(self, event: GeofenceEvent) -> Optional[StayResult]:
        key = (event.object_id, event.fence_name)
        if event.event_type == EventType.ENTER:
            self._entries[key] = self._clock()
            return None
        if event.event_type == EventType.EXIT:
            entered_at = self._entries.pop(key, None)
            if entered_at is None:
                return None
            duration = self._clock() - entered_at
            if duration >= self._min_seconds:
                result = StayResult(
                    object_id=event.object_id,
                    fence_name=event.fence_name,
                    duration_seconds=duration,
                    entered_at=entered_at,
                )
                for cb in self._callbacks.values():
                    cb(result)
                return result
        return None

    def active_count(self) -> int:
        """Number of (object, fence) pairs currently being tracked."""
        return len(self._entries)

    def reset(self) -> None:
        self._entries.clear()
