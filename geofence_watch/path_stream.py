"""Stream wrapper that feeds events into a PathTracker."""
from __future__ import annotations

from typing import Callable, Optional, Tuple

from .event import GeofenceEvent
from .path_tracker import PathRecord, PathTracker


class PathStream:
    """Connects a GeofenceEvent source to a PathTracker.

    Usage::

        stream = PathStream()
        stream.add_callback("print", lambda r: print(r))
        stream.process(event)
    """

    def __init__(
        self,
        tracker: Optional[PathTracker] = None,
        max_path_length: Optional[int] = None,
        track_objects: Optional[Tuple[str, ...]] = None,
    ) -> None:
        if tracker is not None and not isinstance(tracker, PathTracker):
            raise TypeError("tracker must be a PathTracker instance or None")
        self._tracker = tracker or PathTracker(
            max_path_length=max_path_length,
            track_objects=track_objects,
        )

    @property
    def tracker(self) -> PathTracker:
        return self._tracker

    def process(self, event: GeofenceEvent) -> None:
        """Feed a single event into the tracker."""
        if not isinstance(event, GeofenceEvent):
            raise TypeError("event must be a GeofenceEvent")
        self._tracker.ingest(event)

    def add_callback(self, name: str, cb: Callable[[PathRecord], None]) -> None:
        self._tracker.add_callback(name, cb)

    def remove_callback(self, name: str) -> None:
        self._tracker.remove_callback(name)

    @property
    def callback_names(self) -> Tuple[str, ...]:
        return self._tracker.callback_names

    def path_for(self, object_id: str) -> Optional[PathRecord]:
        return self._tracker.path_for(object_id)
