"""Stream wrapper that feeds GeofenceEvents into a DwellTracker and
notifies registered callbacks with updated DwellRecord snapshots."""

from __future__ import annotations

from typing import Callable, Dict, List

from .dwell_tracker import DwellRecord, DwellTracker
from .event import GeofenceEvent


class DwellStream:
    """Connects an event source to a :class:`DwellTracker`.

    Callbacks receive a :class:`DwellRecord` every time an event causes
    the tracker state to change (enter or exit).
    """

    def __init__(self, tracker: DwellTracker | None = None) -> None:
        if tracker is not None and not isinstance(tracker, DwellTracker):
            raise TypeError("tracker must be a DwellTracker instance or None")
        self._tracker: DwellTracker = tracker if tracker is not None else DwellTracker()
        self._callbacks: Dict[str, Callable[[DwellRecord], None]] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def tracker(self) -> DwellTracker:
        """The underlying :class:`DwellTracker`."""
        return self._tracker

    @property
    def callback_names(self) -> List[str]:
        """Registered callback names in insertion order."""
        return list(self._callbacks.keys())

    # ------------------------------------------------------------------
    # Callback management
    # ------------------------------------------------------------------

    def add_callback(self, name: str, fn: Callable[[DwellRecord], None]) -> None:
        """Register *fn* under *name*. Raises :class:`ValueError` on duplicate."""
        if not callable(fn):
            raise TypeError("fn must be callable")
        if name in self._callbacks:
            raise ValueError(f"Callback '{name}' is already registered")
        self._callbacks[name] = fn

    def remove_callback(self, name: str) -> None:
        """Unregister the callback identified by *name*."""
        if name not in self._callbacks:
            raise KeyError(f"No callback named '{name}'")
        del self._callbacks[name]

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self, event: GeofenceEvent) -> DwellRecord | None:
        """Feed *event* into the tracker.

        Returns the resulting :class:`DwellRecord` if the tracker updated
        its state, otherwise ``None``.  All registered callbacks are
        invoked with the record when one is produced.
        """
        record = self._tracker.ingest(event)
        if record is not None:
            for fn in self._callbacks.values():
                fn(record)
        return record

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"DwellStream(callbacks={len(self._callbacks)}, "
            f"tracker={self._tracker!r})"
        )
