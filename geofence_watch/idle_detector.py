"""Detect objects that have not generated any event within a configurable
time window (idle / stale-object detection)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .event import GeofenceEvent


@dataclass
class IdleRecord:
    """Snapshot of an object's idle state."""

    object_id: str
    last_seen: float          # epoch seconds
    idle_seconds: float       # how long since last event
    last_fence: Optional[str] = None

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"IdleRecord(object_id={self.object_id!r}, "
            f"idle_seconds={self.idle_seconds:.1f}, "
            f"last_fence={self.last_fence!r})"
        )


class IdleDetector:
    """Track last-seen timestamps and report objects idle longer than a threshold.

    Parameters
    ----------
    threshold_seconds:
        Minimum seconds of silence before an object is considered idle.
    clock:
        Callable returning current epoch time; defaults to ``time.time``.
        Useful for deterministic testing.
    """

    def __init__(
        self,
        threshold_seconds: float = 60.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if threshold_seconds <= 0:
            raise ValueError("threshold_seconds must be positive")
        self._threshold = threshold_seconds
        self._clock = clock
        self._last_seen: Dict[str, Tuple[float, Optional[str]]] = {}
        self._callbacks: List[Callable[[List[IdleRecord]], None]] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def threshold_seconds(self) -> float:
        return self._threshold

    @property
    def tracked_objects(self) -> List[str]:
        return list(self._last_seen.keys())

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest(self, event: GeofenceEvent) -> None:
        """Update the last-seen timestamp for the event's object."""
        self._last_seen[event.object_id] = (self._clock(), event.fence_name)

    # ------------------------------------------------------------------
    # Idle query
    # ------------------------------------------------------------------

    def idle_objects(self) -> List[IdleRecord]:
        """Return records for every object currently exceeding the threshold."""
        now = self._clock()
        results: List[IdleRecord] = []
        for obj_id, (last_ts, fence) in self._last_seen.items():
            elapsed = now - last_ts
            if elapsed >= self._threshold:
                results.append(
                    IdleRecord(
                        object_id=obj_id,
                        last_seen=last_ts,
                        idle_seconds=elapsed,
                        last_fence=fence,
                    )
                )
        return results

    def check_and_notify(self) -> List[IdleRecord]:
        """Compute idle objects and fire registered callbacks."""
        records = self.idle_objects()
        if records:
            for cb in list(self._callbacks):
                cb(records)
        return records

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def add_callback(self, cb: Callable[[List[IdleRecord]], None]) -> None:
        if not callable(cb):
            raise TypeError("cb must be callable")
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[List[IdleRecord]], None]) -> None:
        self._callbacks = [c for c in self._callbacks if c is not cb]

    @property
    def callback_names(self) -> List[str]:
        return [getattr(c, "__name__", repr(c)) for c in self._callbacks]
