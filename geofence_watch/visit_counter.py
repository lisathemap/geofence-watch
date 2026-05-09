"""Tracks how many times each object has visited each geofence."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

from .event import EventType, GeofenceEvent


@dataclass
class VisitKey:
    object_id: str
    fence_name: str

    def as_tuple(self) -> Tuple[str, str]:
        return (self.object_id, self.fence_name)


class VisitCounter:
    """Counts ENTER events per (object_id, fence_name) pair.

    Only EventType.ENTER increments the visit count; EXIT events are ignored.
    """

    def __init__(self, track_objects: Optional[Tuple[str, ...]] = None) -> None:
        if track_objects is not None:
            track_objects = tuple(track_objects)
        self._track_objects = track_objects
        self._counts: Dict[Tuple[str, str], int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def track_objects(self) -> Optional[Tuple[str, ...]]:
        return self._track_objects

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def ingest(self, event: GeofenceEvent) -> None:
        """Process a single event, incrementing the counter on ENTER."""
        if event.event_type is not EventType.ENTER:
            return
        if self._track_objects is not None and event.object_id not in self._track_objects:
            return
        key = (event.object_id, event.fence_name)
        self._counts[key] += 1

    def reset(self, object_id: Optional[str] = None, fence_name: Optional[str] = None) -> None:
        """Reset counters.  Pass both args to clear a single cell, one arg to
        clear a row/column, or neither to clear everything."""
        if object_id is None and fence_name is None:
            self._counts.clear()
            return
        keys = [k for k in self._counts if
                (object_id is None or k[0] == object_id) and
                (fence_name is None or k[1] == fence_name)]
        for k in keys:
            del self._counts[k]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def count(self, object_id: str, fence_name: str) -> int:
        """Return visit count for the given pair (0 if never visited)."""
        return self._counts.get((object_id, fence_name), 0)

    def total_for_object(self, object_id: str) -> int:
        """Sum of all fence visits for a single object."""
        return sum(v for (oid, _), v in self._counts.items() if oid == object_id)

    def total_for_fence(self, fence_name: str) -> int:
        """Sum of all object visits for a single fence."""
        return sum(v for (_, fn), v in self._counts.items() if fn == fence_name)

    def snapshot(self) -> Dict[Tuple[str, str], int]:
        """Return a shallow copy of the current counts."""
        return dict(self._counts)

    def __repr__(self) -> str:  # pragma: no cover
        return f"VisitCounter(pairs={len(self._counts)}, track_objects={self._track_objects})"
