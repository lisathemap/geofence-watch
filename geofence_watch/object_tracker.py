"""Tracks the last known position and fence state for each object ID."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional

from .event import EventType, GeofenceEvent
from .point import Point


@dataclass
class ObjectState:
    """Snapshot of a single tracked object."""

    object_id: str
    last_point: Optional[Point] = None
    active_fences: FrozenSet[str] = field(default_factory=frozenset)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ObjectState(object_id={self.object_id!r}, "
            f"last_point={self.last_point!r}, "
            f"active_fences={sorted(self.active_fences)!r})"
        )


class ObjectTracker:
    """Maintains per-object state by consuming GeofenceEvents.

    Each ENTER event adds the fence to the object's active set.
    Each EXIT event removes it.  The latest Point is always stored.
    """

    def __init__(self) -> None:
        self._states: Dict[str, ObjectState] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def ingest(self, event: GeofenceEvent) -> None:
        """Update internal state from *event*."""
        if not isinstance(event, GeofenceEvent):
            raise TypeError(f"Expected GeofenceEvent, got {type(event).__name__}")

        oid = event.object_id
        state = self._states.setdefault(
            oid, ObjectState(object_id=oid)
        )
        state.last_point = event.point

        fences = set(state.active_fences)
        if event.event_type is EventType.ENTER:
            fences.add(event.fence_name)
        elif event.event_type is EventType.EXIT:
            fences.discard(event.fence_name)
        state.active_fences = frozenset(fences)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def state_for(self, object_id: str) -> Optional[ObjectState]:
        """Return the current state for *object_id*, or ``None``."""
        return self._states.get(object_id)

    def is_inside(self, object_id: str, fence_name: str) -> bool:
        """Return ``True`` if *object_id* is currently inside *fence_name*."""
        state = self._states.get(object_id)
        return state is not None and fence_name in state.active_fences

    @property
    def object_ids(self) -> FrozenSet[str]:
        """All object IDs seen so far."""
        return frozenset(self._states)

    def reset(self, object_id: Optional[str] = None) -> None:
        """Clear state for *object_id*, or all objects if ``None``."""
        if object_id is None:
            self._states.clear()
        else:
            self._states.pop(object_id, None)

    def __len__(self) -> int:
        return len(self._states)

    def __repr__(self) -> str:  # pragma: no cover
        return f"ObjectTracker(tracked={len(self)})"
