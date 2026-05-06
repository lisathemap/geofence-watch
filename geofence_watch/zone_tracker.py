"""Zone tracker: maintains current zone membership for tracked objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from geofence_watch.event import EventType, GeofenceEvent


@dataclass
class ZoneTracker:
    """Track which fences each object currently occupies.

    Listens to a stream of GeofenceEvents and maintains an up-to-date
    mapping of object_id -> set of fence names the object is inside.
    """

    _zones: Dict[str, Set[str]] = field(default_factory=dict, init=False, repr=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, event: GeofenceEvent) -> None:
        """Update zone membership based on *event*."""
        obj = event.object_id
        fence = event.fence_name

        if obj not in self._zones:
            self._zones[obj] = set()

        if event.event_type is EventType.ENTER:
            self._zones[obj].add(fence)
        elif event.event_type is EventType.EXIT:
            self._zones[obj].discard(fence)

    def zones_for(self, object_id: str) -> Set[str]:
        """Return the set of fence names *object_id* is currently inside."""
        return set(self._zones.get(object_id, set()))

    def objects_in(self, fence_name: str) -> Set[str]:
        """Return all object IDs currently inside *fence_name*."""
        return {obj for obj, fences in self._zones.items() if fence_name in fences}

    def is_inside(self, object_id: str, fence_name: str) -> bool:
        """Return True if *object_id* is currently inside *fence_name*."""
        return fence_name in self._zones.get(object_id, set())

    def remove_object(self, object_id: str) -> None:
        """Remove all zone data for *object_id*."""
        self._zones.pop(object_id, None)

    def clear(self) -> None:
        """Reset all tracked state."""
        self._zones.clear()

    @property
    def tracked_objects(self) -> Set[str]:
        """Return the set of all object IDs currently being tracked."""
        return set(self._zones.keys())

    def __len__(self) -> int:
        return len(self._zones)

    def __repr__(self) -> str:  # pragma: no cover
        return f"ZoneTracker(objects={len(self._zones)})"
