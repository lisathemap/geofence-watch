"""Tracks how many times each object has entered each fence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

from .event import EventType, GeofenceEvent


@dataclass(frozen=True)
class EntryKey:
    object_id: str
    fence_name: str

    def as_tuple(self) -> Tuple[str, str]:
        return (self.object_id, self.fence_name)


class EntryCounter:
    """Counts ENTER events per (object_id, fence_name) pair."""

    def __init__(
        self,
        track_objects: Optional[Tuple[str, ...]] = None,
        track_fences: Optional[Tuple[str, ...]] = None,
    ) -> None:
        if track_objects is not None:
            track_objects = tuple(track_objects)
        if track_fences is not None:
            track_fences = tuple(track_fences)
        self._track_objects = track_objects
        self._track_fences = track_fences
        self._counts: Dict[EntryKey, int] = {}
        self._callbacks: Dict[str, Callable[[EntryKey, int], None]] = {}

    @property
    def track_objects(self) -> Optional[Tuple[str, ...]]:
        return self._track_objects

    @property
    def track_fences(self) -> Optional[Tuple[str, ...]]:
        return self._track_fences

    def ingest(self, event: GeofenceEvent) -> None:
        if event.event_type is not EventType.ENTER:
            return
        if self._track_objects is not None and event.object_id not in self._track_objects:
            return
        if self._track_fences is not None and event.fence_name not in self._track_fences:
            return
        key = EntryKey(object_id=event.object_id, fence_name=event.fence_name)
        self._counts[key] = self._counts.get(key, 0) + 1
        for cb in self._callbacks.values():
            cb(key, self._counts[key])

    def count(self, object_id: str, fence_name: str) -> int:
        return self._counts.get(EntryKey(object_id=object_id, fence_name=fence_name), 0)

    def total(self) -> int:
        return sum(self._counts.values())

    def add_callback(self, name: str, cb: Callable[[EntryKey, int], None]) -> None:
        if not callable(cb):
            raise TypeError(f"callback must be callable, got {type(cb)!r}")
        self._callbacks[name] = cb

    def remove_callback(self, name: str) -> None:
        self._callbacks.pop(name, None)

    def reset(self) -> None:
        self._counts.clear()

    def __repr__(self) -> str:
        return (
            f"EntryCounter(track_objects={self._track_objects!r}, "
            f"track_fences={self._track_fences!r}, total={self.total()})"
        )
