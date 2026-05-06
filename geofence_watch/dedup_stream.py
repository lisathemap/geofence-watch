"""High-level stream wrapper that integrates EventDeduplicator with GeofenceStream."""

from __future__ import annotations

from typing import Callable, List, Optional

from .deduplicator import EventDeduplicator
from .event import GeofenceEvent
from .point import Point
from .stream import GeofenceStream


class DedupStream:
    """Wraps a :class:`~geofence_watch.stream.GeofenceStream` and transparently
    deduplicates events before forwarding them to registered callbacks.

    Example usage::

        ds = DedupStream(stream)
        ds.add_callback(print)
        ds.process("truck-1", point)   # delegates to underlying stream
    """

    def __init__(self, stream: GeofenceStream) -> None:
        self._stream = stream
        self._deduplicator = EventDeduplicator()
        # Wire stream output into our deduplicator
        self._stream.add_callback(self._deduplicator.feed)

    # ------------------------------------------------------------------
    # Delegation helpers
    # ------------------------------------------------------------------

    def process(self, object_id: str, point: Point) -> List[GeofenceEvent]:
        """Process *point* for *object_id* through the underlying stream.

        Returns the list of raw events produced by the stream (before
        deduplication).  Deduplicated events are forwarded asynchronously to
        callbacks registered on this :class:`DedupStream`.
        """
        return self._stream.process(object_id, point)

    # ------------------------------------------------------------------
    # Callback management (forwarded to deduplicator)
    # ------------------------------------------------------------------

    def add_callback(self, cb: Callable[[GeofenceEvent], None]) -> None:
        """Register *cb* to receive deduplicated events."""
        self._deduplicator.add_callback(cb)

    def remove_callback(self, cb: Callable[[GeofenceEvent], None]) -> None:
        """Unregister *cb*."""
        self._deduplicator.remove_callback(cb)

    # ------------------------------------------------------------------
    # Deduplicator access
    # ------------------------------------------------------------------

    @property
    def deduplicator(self) -> EventDeduplicator:
        """The underlying :class:`EventDeduplicator` instance."""
        return self._deduplicator

    @property
    def stream(self) -> GeofenceStream:
        """The underlying :class:`GeofenceStream` instance."""
        return self._stream

    def __repr__(self) -> str:  # pragma: no cover
        return f"DedupStream(stream={self._stream!r})"
