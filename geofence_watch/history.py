"""Tracks per-object geofence event history with optional max-size cap."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterator, Optional

from .event import GeofenceEvent


@dataclass
class ObjectHistory:
    """Stores the event log for a single tracked object."""

    object_id: str
    max_events: Optional[int] = None
    _events: Deque[GeofenceEvent] = field(default_factory=deque, init=False, repr=False)

    def record(self, event: GeofenceEvent) -> None:
        """Append *event* to the history, evicting the oldest if capped."""
        if self.max_events is not None and len(self._events) >= self.max_events:
            self._events.popleft()
        self._events.append(event)

    def latest(self) -> Optional[GeofenceEvent]:
        """Return the most recent event, or *None* if history is empty."""
        return self._events[-1] if self._events else None

    def __iter__(self) -> Iterator[GeofenceEvent]:
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def __repr__(self) -> str:  # pragma: no cover
        return f"ObjectHistory(object_id={self.object_id!r}, events={len(self._events)})"


class HistoryStore:
    """Central registry mapping object IDs to their :class:`ObjectHistory`."""

    def __init__(self, max_events_per_object: Optional[int] = None) -> None:
        self._max = max_events_per_object
        self._store: Dict[str, ObjectHistory] = {}

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def record(self, event: GeofenceEvent) -> None:
        """Record *event* under the appropriate object history bucket."""
        oid = event.object_id
        if oid not in self._store:
            self._store[oid] = ObjectHistory(object_id=oid, max_events=self._max)
        self._store[oid].record(event)

    def clear(self, object_id: str) -> None:
        """Remove all history for *object_id*."""
        self._store.pop(object_id, None)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get(self, object_id: str) -> Optional[ObjectHistory]:
        """Return the :class:`ObjectHistory` for *object_id*, or *None*."""
        return self._store.get(object_id)

    def object_ids(self) -> list[str]:
        """Return a sorted list of all tracked object IDs."""
        return sorted(self._store.keys())

    def __len__(self) -> int:
        return len(self._store)

    def __repr__(self) -> str:  # pragma: no cover
        return f"HistoryStore(objects={len(self._store)}, cap={self._max})"
