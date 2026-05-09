"""Per-object, per-fence event counting with optional reset support."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from geofence_watch.event import EventType, GeofenceEvent


@dataclass
class CounterKey:
    object_id: str
    fence_name: str
    event_type: EventType

    def as_tuple(self) -> Tuple[str, str, EventType]:
        return (self.object_id, self.fence_name, self.event_type)


class EventCounter:
    """Counts GeofenceEvents grouped by object_id, fence_name, and event_type.

    Parameters
    ----------
    track_types:
        If provided, only events whose type is in this collection are counted.
        Pass ``None`` (default) to count all event types.
    """

    def __init__(self, track_types: Optional[Tuple[EventType, ...]] = None) -> None:
        if track_types is not None:
            track_types = tuple(track_types)
        self._track_types = track_types
        self._counts: Dict[Tuple[str, str, EventType], int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def ingest(self, event: GeofenceEvent) -> None:
        """Record *event* if it passes the type filter."""
        if not isinstance(event, GeofenceEvent):
            raise TypeError(f"Expected GeofenceEvent, got {type(event).__name__}")
        if self._track_types is not None and event.event_type not in self._track_types:
            return
        key = (event.object_id, event.fence_name, event.event_type)
        self._counts[key] += 1

    def reset(self, object_id: Optional[str] = None) -> None:
        """Reset counters.  If *object_id* is given, only that object is cleared."""
        if object_id is None:
            self._counts.clear()
        else:
            keys_to_delete = [k for k in self._counts if k[0] == object_id]
            for k in keys_to_delete:
                del self._counts[k]

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def count(
        self,
        object_id: str,
        fence_name: str,
        event_type: EventType,
    ) -> int:
        """Return the count for a specific (object, fence, type) combination."""
        return self._counts.get((object_id, fence_name, event_type), 0)

    def total_for_object(self, object_id: str) -> int:
        """Return the total event count across all fences and types for *object_id*."""
        return sum(v for (oid, _, _), v in self._counts.items() if oid == object_id)

    def total_for_fence(self, fence_name: str) -> int:
        """Return the total event count across all objects and types for *fence_name*."""
        return sum(v for (_, fn, _), v in self._counts.items() if fn == fence_name)

    @property
    def total(self) -> int:
        """Grand total of all recorded events."""
        return sum(self._counts.values())

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventCounter(total={self.total}, keys={len(self._counts)})"
