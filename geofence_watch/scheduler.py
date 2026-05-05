"""Periodic snapshot scheduler for geofence activity reporting."""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional


class SnapshotScheduler:
    """Calls a snapshot callback at a fixed interval in a background thread.

    Parameters
    ----------
    interval:
        Seconds between each snapshot invocation.
    callback:
        Callable invoked on each tick; receives the current tick count (int).
    """

    def __init__(self, interval: float, callback: Callable[[int], None]) -> None:
        if interval <= 0:
            raise ValueError("interval must be a positive number")
        self._interval = interval
        self._callback = callback
        self._tick: int = 0
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background scheduler thread."""
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Scheduler is already running")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the scheduler to stop and wait for the thread to finish."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 1)
            self._thread = None

    @property
    def is_running(self) -> bool:
        """Return True if the scheduler thread is currently active."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def tick(self) -> int:
        """Number of ticks fired since the last start."""
        return self._tick

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SnapshotScheduler(interval={self._interval}, "
            f"running={self.is_running}, tick={self._tick})"
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self) -> None:
        self._tick = 0
        while not self._stop_event.wait(timeout=self._interval):
            self._tick += 1
            try:
                self._callback(self._tick)
            except Exception:  # noqa: BLE001
                pass  # keep the scheduler alive even if the callback raises
