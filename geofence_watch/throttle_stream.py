"""ThrottleStream: wraps a GeofenceStream and filters events through an EventThrottle."""

from __future__ import annotations

from typing import Callable, List, Optional

from .event import GeofenceEvent
from .stream import GeofenceStream
from .throttle import EventThrottle


class ThrottleStream:
    """Processes coordinate updates via an underlying :class:`GeofenceStream` and
    forwards :class:`GeofenceEvent` objects only when they pass the throttle.

    Parameters
    ----------
    stream:
        The underlying :class:`GeofenceStream` to delegate coordinate processing to.
    throttle:
        An :class:`EventThrottle` instance controlling the cooldown window.
    """

    def __init__(self, stream: GeofenceStream, throttle: EventThrottle) -> None:
        self._stream = stream
        self._throttle = throttle
        self._callbacks: List[Callable[[GeofenceEvent], None]] = []

    @property
    def throttle(self) -> EventThrottle:
        return self._throttle

    def add_callback(self, fn: Callable[[GeofenceEvent], None]) -> None:
        """Register a callback that receives throttle-passed events."""
        if fn not in self._callbacks:
            self._callbacks.append(fn)

    def remove_callback(self, fn: Callable[[GeofenceEvent], None]) -> None:
        """Unregister a previously added callback."""
        self._callbacks = [cb for cb in self._callbacks if cb is not fn]

    def process(self, object_id: str, lon: float, lat: float) -> List[GeofenceEvent]:
        """Process a coordinate update and return throttle-approved events.

        All events produced by the underlying stream are evaluated; only those
        that pass :meth:`EventThrottle.allow` are returned and forwarded to
        registered callbacks.
        """
        raw_events = self._stream.process(object_id, lon, lat)
        approved: List[GeofenceEvent] = []
        for evt in raw_events:
            if self._throttle.allow(evt):
                approved.append(evt)
                for cb in self._callbacks:
                    cb(evt)
        return approved

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ThrottleStream(stream={self._stream!r}, throttle={self._throttle!r})"
        )
