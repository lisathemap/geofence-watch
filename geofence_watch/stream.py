"""Stream processor that tracks state and emits geofence events."""

from typing import Callable, Dict, Iterator, List, Optional

from .checker import GeofenceChecker
from .event import EventType, GeofenceEvent
from .point import Point


EventCallback = Callable[[GeofenceEvent], None]


class GeofenceStream:
    """Processes a stream of points and emits boundary-crossing events.

    Tracks per-fence inside/outside state so that ENTER and EXIT events
    are only emitted on actual transitions.
    """

    def __init__(
        self,
        checker: GeofenceChecker,
        on_event: Optional[EventCallback] = None,
        emit_steady_state: bool = False,
    ) -> None:
        self._checker = checker
        self._on_event = on_event
        self._emit_steady_state = emit_steady_state
        # fence_name -> last known inside state (None = unknown)
        self._state: Dict[str, Optional[bool]] = {}

    def _get_state(self, fence_name: str) -> Optional[bool]:
        return self._state.get(fence_name)

    def process(self, point: Point, metadata: Optional[dict] = None) -> List[GeofenceEvent]:
        """Process a single point and return any generated events."""
        events: List[GeofenceEvent] = []

        for fence_name in self._checker.fence_names:
            inside_now = self._checker.check(point, fence_name)
            prev = self._get_state(fence_name)

            if prev is None:
                # First observation — emit steady-state event if requested
                event_type = EventType.INSIDE if inside_now else EventType.OUTSIDE
                if self._emit_steady_state:
                    events.append(GeofenceEvent(fence_name, event_type, point, metadata=metadata))
            elif inside_now and not prev:
                events.append(GeofenceEvent(fence_name, EventType.ENTER, point, metadata=metadata))
            elif not inside_now and prev:
                events.append(GeofenceEvent(fence_name, EventType.EXIT, point, metadata=metadata))
            elif self._emit_steady_state:
                event_type = EventType.INSIDE if inside_now else EventType.OUTSIDE
                events.append(GeofenceEvent(fence_name, event_type, point, metadata=metadata))

            self._state[fence_name] = inside_now

        for event in events:
            if self._on_event:
                self._on_event(event)

        return events

    def process_many(self, points: Iterator[Point]) -> List[GeofenceEvent]:
        """Process an iterable of points, returning all generated events."""
        all_events: List[GeofenceEvent] = []
        for point in points:
            all_events.extend(self.process(point))
        return all_events

    def reset_state(self) -> None:
        """Clear all tracked fence states (useful for testing or re-runs)."""
        self._state.clear()
