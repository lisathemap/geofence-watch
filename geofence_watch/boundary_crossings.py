"""Track and count boundary crossing events per object/fence pair."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .event import EventType, GeofenceEvent


@dataclass
class CrossingRecord:
    """Aggregated crossing statistics for one (object_id, fence_name) pair."""

    object_id: str
    fence_name: str
    enter_count: int = 0
    exit_count: int = 0

    @property
    def total(self) -> int:
        """Total number of boundary crossings (enters + exits)."""
        return self.enter_count + self.exit_count

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"CrossingRecord(object_id={self.object_id!r}, "
            f"fence_name={self.fence_name!r}, "
            f"enter={self.enter_count}, exit={self.exit_count})"
        )


class BoundaryCrossingTracker:
    """Counts ENTER and EXIT events per (object_id, fence_name) pair.

    Parameters
    ----------
    max_history:
        If given, only the most recent *max_history* crossing events are kept
        in the raw event log for each key.  Set to ``None`` (default) for
        unlimited storage.
    """

    def __init__(self, max_history: Optional[int] = None) -> None:
        if max_history is not None and max_history <= 0:
            raise ValueError("max_history must be a positive integer or None")
        self._max_history = max_history
        self._records: Dict[Tuple[str, str], CrossingRecord] = {}
        self._log: Dict[Tuple[str, str], List[GeofenceEvent]] = defaultdict(list)
        self._callbacks: List[Callable[[CrossingRecord], None]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, event: GeofenceEvent) -> None:
        """Process a single GeofenceEvent and update crossing counts."""
        if event.event_type not in (EventType.ENTER, EventType.EXIT):
            return

        key: Tuple[str, str] = (event.object_id, event.fence_name)
        if key not in self._records:
            self._records[key] = CrossingRecord(
                object_id=event.object_id, fence_name=event.fence_name
            )

        rec = self._records[key]
        if event.event_type is EventType.ENTER:
            rec.enter_count += 1
        else:
            rec.exit_count += 1

        log = self._log[key]
        log.append(event)
        if self._max_history is not None:
            del log[: max(0, len(log) - self._max_history)]

        for cb in list(self._callbacks):
            cb(rec)

    def record_for(self, object_id: str, fence_name: str) -> Optional[CrossingRecord]:
        """Return the CrossingRecord for a pair, or None if not seen."""
        return self._records.get((object_id, fence_name))

    def all_records(self) -> List[CrossingRecord]:
        """Return all crossing records sorted by (object_id, fence_name)."""
        return sorted(self._records.values(), key=lambda r: (r.object_id, r.fence_name))

    def events_for(self, object_id: str, fence_name: str) -> List[GeofenceEvent]:
        """Return the raw event log for a pair."""
        return list(self._log.get((object_id, fence_name), []))

    def reset(self) -> None:
        """Clear all accumulated data."""
        self._records.clear()
        self._log.clear()

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def add_callback(self, cb: Callable[[CrossingRecord], None]) -> None:
        """Register a callback invoked after each crossing update."""
        if not callable(cb):
            raise TypeError("cb must be callable")
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[CrossingRecord], None]) -> None:
        """Unregister a previously added callback."""
        self._callbacks = [c for c in self._callbacks if c is not cb]

    @property
    def callback_count(self) -> int:
        return len(self._callbacks)
