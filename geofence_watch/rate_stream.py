"""RateStream: wraps a RateMonitor and forwards events to registered callbacks."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from geofence_watch.event import GeofenceEvent
from geofence_watch.rate_monitor import RateMonitor

_Callback = Callable[[GeofenceEvent, float], None]


class RateStream:
    """Pipeline stage that records events and notifies callbacks with the
    current event rate after each ingestion.

    Parameters
    ----------
    window_seconds:
        Rolling window forwarded to the underlying :class:`RateMonitor`.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._monitor = RateMonitor(window_seconds=window_seconds)
        self._callbacks: Dict[str, _Callback] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def monitor(self) -> RateMonitor:
        """Underlying :class:`RateMonitor` instance."""
        return self._monitor

    @property
    def callback_names(self) -> List[str]:
        return list(self._callbacks.keys())

    # ------------------------------------------------------------------
    # Callback management
    # ------------------------------------------------------------------

    def add_callback(self, name: str, fn: _Callback) -> None:
        """Register *fn* under *name*.  Raises ``ValueError`` on duplicate."""
        if not callable(fn):
            raise TypeError("fn must be callable")
        if name in self._callbacks:
            raise ValueError(f"Callback '{name}' already registered")
        self._callbacks[name] = fn

    def remove_callback(self, name: str) -> None:
        """Remove the callback registered under *name*."""
        if name not in self._callbacks:
            raise KeyError(f"No callback named '{name}'")
        del self._callbacks[name]

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def feed(self, event: GeofenceEvent, *, _now: Optional[float] = None) -> float:
        """Ingest *event*, update the monitor, notify callbacks, and return
        the current rate (events/second)."""
        self._monitor.record(event, _now=_now)
        current_rate = self._monitor.rate(_now=_now)
        for fn in self._callbacks.values():
            fn(event, current_rate)
        return current_rate

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RateStream(window_seconds={self._monitor.window_seconds}, "
            f"callbacks={self.callback_names})"
        )
