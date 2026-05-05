"""Stateful stream processor that emits GeofenceEvents and records history."""

from __future__ import annotations

from typing import Dict, Iterator, List, Optional

from .checker import GeofenceChecker
from .event import EventType, GeofenceEvent
from .history import HistoryStore
from .point import Point


class GeofenceStream:
    """Process a stream of (object_id, Point) observations.

    Maintains the last-known inside/outside state per (object_id, fence)
    pair and emits :class:`~geofence_watch.event.GeofenceEvent` objects
    only when the state changes (enter / exit transitions).

    Parameters
    ----------
    checker:
        A configured :class:`~geofence_watch.checker.GeofenceChecker`.
    max_history:
        Optional cap on stored events per object.  ``None`` means unlimited.
    """

    def __init__(
        self,
        checker: GeofenceChecker,
        max_history: Optional[int] = None,
    ) -> None:
        self._checker = checker
        # state[object_id][fence_name] -> bool (True = inside)
        self._state: Dict[str, Dict[str, bool]] = {}
        self.history: HistoryStore = HistoryStore(max_events_per_object=max_history)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_state(self, object_id: str, fence_name: str) -> Optional[bool]:
        return self._state.get(object_id, {}).get(fence_name)

    def _set_state(self, object_id: str, fence_name: str, inside: bool) -> None:
        self._state.setdefault(object_id, {})[fence_name] = inside

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, object_id: str, point: Point) -> List[GeofenceEvent]:
        """Evaluate *point* for *object_id* and return any transition events."""
        events: List[GeofenceEvent] = []

        for fence_name in self._checker.fence_names:
            inside_now = self._checker.check(fence_name, point)
            was_inside = self._get_state(object_id, fence_name)\n
            if was_inside is None:
                # First observation — seed state without emitting an event.
                self._set_state(object_id, fence_name, inside_now)
                continue

            if inside_now == was_inside:
                continue

            event_type = EventType.ENTER if inside_now else EventType.EXIT
            event = GeofenceEvent(
                object_id=object_id,
                fence_name=fence_name,
                event_type=event_type,
                point=point,
            )
            self._set_state(object_id, fence_name, inside_now)
            self.history.record(event)
            events.append(event)

        return events

    def process_many(
        self, object_id: str, points: List[Point]
    ) -> Iterator[GeofenceEvent]:
        """Yield transition events for each point in *points* sequentially."""
        for point in points:
            yield from self.process(object_id, point)

    def reset(self, object_id: Optional[str] = None) -> None:
        """Clear state (and history) for *object_id*, or everything if *None*."""
        if object_id is None:
            self._state.clear()
            # Rebuild a fresh store preserving the same cap.
            self.history = HistoryStore(
                max_events_per_object=self.history._max
            )
        else:
            self._state.pop(object_id, None)
            self.history.clear(object_id)
