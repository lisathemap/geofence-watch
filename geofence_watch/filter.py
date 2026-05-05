"""Event filtering utilities for geofence-watch."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional

from geofence_watch.event import EventType, GeofenceEvent


@dataclass
class EventFilter:
    """Composable filter for GeofenceEvent streams.

    Multiple criteria are combined with logical AND – an event must
    satisfy *every* configured criterion to pass through.
    """

    event_types: Optional[List[EventType]] = None
    fence_names: Optional[List[str]] = None
    object_ids: Optional[List[str]] = None
    _custom: List[Callable[[GeofenceEvent], bool]] = field(
        default_factory=list, init=False, repr=False
    )

    def add_custom(self, predicate: Callable[[GeofenceEvent], bool]) -> None:
        """Attach an arbitrary callable predicate to the filter."""
        self._custom.append(predicate)

    def matches(self, event: GeofenceEvent) -> bool:
        """Return True when *event* satisfies all configured criteria."""
        if self.event_types is not None and event.event_type not in self.event_types:
            return False
        if self.fence_names is not None and event.fence_name not in self.fence_names:
            return False
        if self.object_ids is not None and event.object_id not in self.object_ids:
            return False
        return all(p(event) for p in self._custom)

    def apply(self, events: Iterable[GeofenceEvent]) -> List[GeofenceEvent]:
        """Return a list of events from *events* that pass this filter."""
        return [e for e in events if self.matches(e)]

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"EventFilter(event_types={self.event_types!r}, "
            f"fence_names={self.fence_names!r}, "
            f"object_ids={self.object_ids!r}, "
            f"custom_predicates={len(self._custom)})"
        )
