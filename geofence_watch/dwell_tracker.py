"""Track how long objects dwell inside geofence zones."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from geofence_watch.event import EventType, GeofenceEvent


@dataclass
class DwellRecord:
    """Holds entry time and accumulated dwell duration for one object/fence pair."""

    object_id: str
    fence_name: str
    entered_at: float  # monotonic timestamp
    _clock: object = field(default=None, repr=False)

    def elapsed(self) -> float:
        """Return seconds spent inside the fence since entry."""
        now = self._clock() if self._clock is not None else time.monotonic()
        return now - self.entered_at

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"DwellRecord(object_id={self.object_id!r}, "
            f"fence_name={self.fence_name!r}, elapsed={self.elapsed():.2f}s)"
        )


class DwellTracker:
    """Record entry/exit times and report dwell duration per object per fence.

    Parameters
    ----------
    clock:
        Zero-argument callable returning a monotonic float (seconds).  Defaults
        to :func:`time.monotonic`.  Inject a fake clock in tests.
    """

    def __init__(self, clock=None) -> None:
        self._clock = clock or time.monotonic
        # key: (object_id, fence_name) -> DwellRecord
        self._active: Dict[Tuple[str, str], DwellRecord] = {}
        # key: (object_id, fence_name) -> last completed dwell seconds
        self._last_dwell: Dict[Tuple[str, str], float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, event: GeofenceEvent) -> Optional[float]:
        """Process a :class:`GeofenceEvent` and return completed dwell seconds on EXIT.

        Returns
        -------
        float or None
            Seconds the object dwelled inside the fence when it exits, otherwise
            ``None``.
        """
        key = (event.object_id, event.fence_name)

        if event.event_type == EventType.ENTER:
            self._active[key] = DwellRecord(
                object_id=event.object_id,
                fence_name=event.fence_name,
                entered_at=self._clock(),
                _clock=self._clock,
            )
            return None

        if event.event_type == EventType.EXIT:
            record = self._active.pop(key, None)
            if record is None:
                return None
            duration = record.elapsed()
            self._last_dwell[key] = duration
            return duration

        return None

    def current_dwell(self, object_id: str, fence_name: str) -> Optional[float]:
        """Return seconds an object has been inside a fence right now, or ``None``."""
        record = self._active.get((object_id, fence_name))
        return record.elapsed() if record is not None else None

    def last_dwell(self, object_id: str, fence_name: str) -> Optional[float]:
        """Return the most recently completed dwell duration, or ``None``."""
        return self._last_dwell.get((object_id, fence_name))

    def active_objects(self) -> Dict[Tuple[str, str], float]:
        """Return mapping of (object_id, fence_name) -> current elapsed seconds."""
        return {k: v.elapsed() for k, v in self._active.items()}

    def reset(self) -> None:
        """Clear all tracked state."""
        self._active.clear()
        self._last_dwell.clear()
