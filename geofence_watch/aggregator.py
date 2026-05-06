"""Event aggregator: counts and summarises GeofenceEvents over a sliding window."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .event import EventType, GeofenceEvent


@dataclass
class WindowSummary:
    """Aggregated statistics for a single (object_id, fence_name) pair."""

    object_id: str
    fence_name: str
    enter_count: int = 0
    exit_count: int = 0
    dwell_seconds: float = 0.0
    last_enter: Optional[datetime] = None
    last_exit: Optional[datetime] = None

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"WindowSummary(object_id={self.object_id!r}, fence={self.fence_name!r}, "
            f"enters={self.enter_count}, exits={self.exit_count}, "
            f"dwell={self.dwell_seconds:.1f}s)"
        )


class EventAggregator:
    """Accumulates GeofenceEvents and produces per-object, per-fence summaries.

    Parameters
    ----------
    window_seconds:
        Only events whose timestamp falls within *now - window_seconds* are
        included in summaries.  Pass ``None`` to aggregate all events.
    """

    def __init__(self, window_seconds: Optional[float] = None) -> None:
        if window_seconds is not None and window_seconds <= 0:
            raise ValueError("window_seconds must be a positive number or None")
        self._window: Optional[float] = window_seconds
        self._events: List[GeofenceEvent] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, event: GeofenceEvent) -> None:
        """Add a single event to the aggregator."""
        self._events.append(event)

    def ingest_many(self, events: List[GeofenceEvent]) -> None:
        """Add multiple events at once."""
        self._events.extend(events)

    def clear(self) -> None:
        """Remove all stored events."""
        self._events.clear()

    @property
    def event_count(self) -> int:
        """Total number of stored events (before window filtering)."""
        return len(self._events)

    def summarise(self, now: Optional[datetime] = None) -> Dict[str, WindowSummary]:
        """Return a mapping of ``'object_id:fence_name'`` -> :class:`WindowSummary`.

        Parameters
        ----------
        now:
            Reference timestamp used to compute the window cutoff.  Defaults
            to ``datetime.utcnow()``.
        """
        now = now or datetime.utcnow()
        cutoff = (
            now - timedelta(seconds=self._window)
            if self._window is not None
            else None
        )

        summaries: Dict[str, WindowSummary] = {}
        # Track open ENTER events so we can compute dwell time
        open_enters: Dict[str, datetime] = {}

        for evt in sorted(self._events, key=lambda e: e.timestamp):
            if cutoff is not None and evt.timestamp < cutoff:
                continue

            key = f"{evt.object_id}:{evt.fence_name}"
            if key not in summaries:
                summaries[key] = WindowSummary(
                    object_id=evt.object_id, fence_name=evt.fence_name
                )
            summary = summaries[key]

            if evt.event_type == EventType.ENTER:
                summary.enter_count += 1
                summary.last_enter = evt.timestamp
                open_enters[key] = evt.timestamp
            elif evt.event_type == EventType.EXIT:
                summary.exit_count += 1
                summary.last_exit = evt.timestamp
                if key in open_enters:
                    dwell = (evt.timestamp - open_enters.pop(key)).total_seconds()
                    summary.dwell_seconds += dwell

        # For still-open dwells, accumulate up to *now*
        for key, enter_ts in open_enters.items():
            summaries[key].dwell_seconds += (now - enter_ts).total_seconds()

        return summaries
