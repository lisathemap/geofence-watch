"""Stream wrapper that feeds events into an EntryCounter."""

from __future__ import annotations

from typing import Callable, Optional, Tuple

from .entry_counter import EntryCounter, EntryKey
from .event import GeofenceEvent


class EntryStream:
    """Wraps an EntryCounter and processes a stream of GeofenceEvents."""

    def __init__(
        self,
        counter: Optional[EntryCounter] = None,
        track_objects: Optional[Tuple[str, ...]] = None,
        track_fences: Optional[Tuple[str, ...]] = None,
    ) -> None:
        if counter is not None and not isinstance(counter, EntryCounter):
            raise TypeError(f"counter must be an EntryCounter, got {type(counter)!r}")
        self._counter = counter or EntryCounter(
            track_objects=track_objects,
            track_fences=track_fences,
        )

    @property
    def counter(self) -> EntryCounter:
        return self._counter

    def process(self, event: GeofenceEvent) -> None:
        if not isinstance(event, GeofenceEvent):
            raise TypeError(f"expected GeofenceEvent, got {type(event)!r}")
        self._counter.ingest(event)

    def add_callback(self, name: str, cb: Callable[[EntryKey, int], None]) -> None:
        self._counter.add_callback(name, cb)

    def remove_callback(self, name: str) -> None:
        self._counter.remove_callback(name)

    def count(self, object_id: str, fence_name: str) -> int:
        return self._counter.count(object_id, fence_name)

    def total(self) -> int:
        return self._counter.total()

    def reset(self) -> None:
        self._counter.reset()

    def __repr__(self) -> str:
        return f"EntryStream(counter={self._counter!r})"
