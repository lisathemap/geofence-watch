"""Rate monitor: tracks event throughput over a rolling time window."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

from geofence_watch.event import GeofenceEvent


@dataclass
class RateMonitor:
    """Counts events per second over a configurable rolling window.

    Parameters
    ----------
    window_seconds:
        Width of the rolling window used to compute the rate.  Must be > 0.
    """

    window_seconds: float
    _timestamps: Deque[float] = field(default_factory=deque, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, event: GeofenceEvent, *, _now: Optional[float] = None) -> None:
        """Record that *event* was observed at the current time."""
        now = _now if _now is not None else time.monotonic()
        self._timestamps.append(now)
        self._evict(now)

    def rate(self, *, _now: Optional[float] = None) -> float:
        """Return events-per-second over the current rolling window."""
        now = _now if _now is not None else time.monotonic()
        self._evict(now)
        return len(self._timestamps) / self.window_seconds

    def count(self, *, _now: Optional[float] = None) -> int:
        """Return the raw event count inside the current rolling window."""
        now = _now if _now is not None else time.monotonic()
        self._evict(now)
        return len(self._timestamps)

    def reset(self) -> None:
        """Clear all recorded timestamps."""
        self._timestamps.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict(self, now: float) -> None:
        """Remove timestamps older than the rolling window."""
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RateMonitor(window_seconds={self.window_seconds}, "
            f"count={len(self._timestamps)})"
        )
