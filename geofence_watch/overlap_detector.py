"""Detect when an object is simultaneously inside multiple geofences."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Set

from .event import EventType, GeofenceEvent


@dataclass
class OverlapResult:
    """Emitted when an object occupies more than one fence at the same time."""

    object_id: str
    fence_names: FrozenSet[str]
    timestamp: float

    def __repr__(self) -> str:  # pragma: no cover
        names = ", ".join(sorted(self.fence_names))
        return f"OverlapResult(object={self.object_id!r}, fences=[{names}], t={self.timestamp})"


class OverlapDetector:
    """Track per-object fence membership and fire callbacks on overlaps."""

    def __init__(self, min_overlap: int = 2) -> None:
        if min_overlap < 2:
            raise ValueError("min_overlap must be >= 2")
        self._min_overlap = min_overlap
        self._state: Dict[str, Set[str]] = {}
        self._callbacks: Dict[str, Callable[[OverlapResult], None]] = {}

    @property
    def min_overlap(self) -> int:
        return self._min_overlap

    def callback_names(self) -> List[str]:
        return list(self._callbacks)

    def add_callback(self, name: str, fn: Callable[[OverlapResult], None]) -> None:
        if not callable(fn):
            raise TypeError("fn must be callable")
        self._callbacks[name] = fn

    def remove_callback(self, name: str) -> None:
        self._callbacks.pop(name, None)

    def ingest(self, event: GeofenceEvent) -> Optional[OverlapResult]:
        """Update internal state and return an OverlapResult if overlap exists."""
        oid = event.object_id
        fence = event.fence_name

        current = self._state.setdefault(oid, set())

        if event.event_type == EventType.ENTER:
            current.add(fence)
        elif event.event_type == EventType.EXIT:
            current.discard(fence)

        if len(current) >= self._min_overlap:
            result = OverlapResult(
                object_id=oid,
                fence_names=frozenset(current),
                timestamp=event.timestamp,
            )
            for cb in self._callbacks.values():
                cb(result)
            return result
        return None

    def active_fences(self, object_id: str) -> FrozenSet[str]:
        """Return the set of fences the object is currently inside."""
        return frozenset(self._state.get(object_id, set()))

    def reset(self, object_id: Optional[str] = None) -> None:
        if object_id is None:
            self._state.clear()
        else:
            self._state.pop(object_id, None)
