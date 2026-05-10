"""Track the sequence of fences an object has visited over time."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .event import EventType, GeofenceEvent


@dataclass
class PathRecord:
    """Ordered list of (fence_name, timestamp) pairs for one object."""

    object_id: str
    _entries: List[Tuple[str, float]] = field(default_factory=list, repr=False)

    def append(self, fence_name: str, timestamp: float) -> None:
        self._entries.append((fence_name, timestamp))

    @property
    def path(self) -> List[str]:
        """Ordered fence names visited (enter events only)."""
        return [fence for fence, _ in self._entries]

    @property
    def entries(self) -> List[Tuple[str, float]]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:  # pragma: no cover
        return f"PathRecord(object_id={self.object_id!r}, path={self.path})"


class PathTracker:
    """Records the ordered sequence of geofence entries per object.

    Only ENTER events are tracked; EXIT events are ignored.
    """

    def __init__(
        self,
        max_path_length: Optional[int] = None,
        track_objects: Optional[Tuple[str, ...]] = None,
    ) -> None:
        if max_path_length is not None and max_path_length < 1:
            raise ValueError("max_path_length must be a positive integer or None")
        self._max = max_path_length
        self._track = (
            tuple(track_objects) if track_objects is not None else None
        )
        self._records: Dict[str, PathRecord] = {}
        self._callbacks: Dict[str, Callable[[PathRecord], None]] = {}

    @property
    def max_path_length(self) -> Optional[int]:
        return self._max

    @property
    def tracked_objects(self) -> Optional[Tuple[str, ...]]:
        return self._track

    def ingest(self, event: GeofenceEvent) -> None:
        if event.event_type is not EventType.ENTER:
            return
        oid = event.object_id
        if self._track is not None and oid not in self._track:
            return
        if oid not in self._records:
            self._records[oid] = PathRecord(object_id=oid)
        record = self._records[oid]
        record.append(event.fence_name, event.timestamp)
        if self._max is not None:
            record._entries = record._entries[-self._max :]
        for cb in self._callbacks.values():
            cb(record)

    def path_for(self, object_id: str) -> Optional[PathRecord]:
        return self._records.get(object_id)

    def all_paths(self) -> Dict[str, PathRecord]:
        return dict(self._records)

    def add_callback(self, name: str, cb: Callable[[PathRecord], None]) -> None:
        if not callable(cb):
            raise TypeError("cb must be callable")
        self._callbacks[name] = cb

    def remove_callback(self, name: str) -> None:
        self._callbacks.pop(name, None)

    @property
    def callback_names(self) -> Tuple[str, ...]:
        return tuple(self._callbacks)
