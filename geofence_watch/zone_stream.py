"""ZoneStream: wires a GeofenceStream to a ZoneTracker automatically."""

from __future__ import annotations

from typing import Callable, List, Optional, Set

from geofence_watch.event import GeofenceEvent
from geofence_watch.stream import GeofenceStream
from geofence_watch.zone_tracker import ZoneTracker


class ZoneStream:
    """Attach a ZoneTracker to a GeofenceStream.

    Every event emitted by *stream* is automatically ingested by the
    internal ZoneTracker so callers always have a live view of which
    objects are inside which fences.
    """

    def __init__(self, stream: GeofenceStream) -> None:
        self._stream = stream
        self._tracker = ZoneTracker()
        self._callbacks: List[Callable[[GeofenceEvent], None]] = []
        stream.add_callback(self._on_event)

    # ------------------------------------------------------------------
    # Tracker proxy helpers
    # ------------------------------------------------------------------

    @property
    def tracker(self) -> ZoneTracker:
        """The underlying ZoneTracker instance."""
        return self._tracker

    def zones_for(self, object_id: str) -> Set[str]:
        return self._tracker.zones_for(object_id)

    def objects_in(self, fence_name: str) -> Set[str]:
        return self._tracker.objects_in(fence_name)

    def is_inside(self, object_id: str, fence_name: str) -> bool:
        return self._tracker.is_inside(object_id, fence_name)

    # ------------------------------------------------------------------
    # Callback management
    # ------------------------------------------------------------------

    def add_callback(self, cb: Callable[[GeofenceEvent], None]) -> None:
        """Register *cb* to be called after tracker state is updated."""
        if not callable(cb):
            raise TypeError("callback must be callable")
        self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[GeofenceEvent], None]) -> None:
        self._callbacks.remove(cb)

    @property
    def callback_count(self) -> int:
        return len(self._callbacks)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_event(self, event: GeofenceEvent) -> None:
        self._tracker.ingest(event)
        for cb in list(self._callbacks):
            cb(event)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ZoneStream(tracked={len(self._tracker)}, "
            f"callbacks={self.callback_count})"
        )
