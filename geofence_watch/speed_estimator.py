"""Speed estimation between consecutive geofence events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .event import GeofenceEvent
from .proximity import haversine


@dataclass
class SpeedSample:
    """A single speed measurement for an object."""

    object_id: str
    fence_name: str
    speed_mps: float          # metres per second
    distance_m: float
    elapsed_seconds: float

    @property
    def speed_kph(self) -> float:
        """Speed in kilometres per hour."""
        return self.speed_mps * 3.6

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SpeedSample(object_id={self.object_id!r}, "
            f"fence={self.fence_name!r}, "
            f"speed={self.speed_kph:.2f} kph)"
        )


class SpeedEstimator:
    """Estimates object speed from successive geofence events.

    For each object a single previous event is remembered.  When a new
    event arrives the haversine distance and time delta are used to
    derive an instantaneous speed which is forwarded to all registered
    callbacks.
    """

    def __init__(self, min_elapsed_seconds: float = 0.1) -> None:
        if min_elapsed_seconds <= 0:
            raise ValueError("min_elapsed_seconds must be positive")
        self._min_elapsed = min_elapsed_seconds
        self._last: Dict[str, GeofenceEvent] = {}
        self._callbacks: List[Callable[[SpeedSample], None]] = []

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def add_callback(self, fn: Callable[[SpeedSample], None]) -> None:
        if not callable(fn):
            raise TypeError("callback must be callable")
        self._callbacks.append(fn)

    def remove_callback(self, fn: Callable[[SpeedSample], None]) -> None:
        self._callbacks.remove(fn)

    @property
    def callback_count(self) -> int:
        return len(self._callbacks)

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def ingest(self, event: GeofenceEvent) -> Optional[SpeedSample]:
        """Process *event* and return a SpeedSample if one can be computed."""
        oid = event.object_id
        sample: Optional[SpeedSample] = None

        if oid in self._last:
            prev = self._last[oid]
            elapsed = event.timestamp - prev.timestamp
            if elapsed >= self._min_elapsed:
                dist = haversine(prev.point, event.point)
                speed = dist / elapsed
                sample = SpeedSample(
                    object_id=oid,
                    fence_name=event.fence_name,
                    speed_mps=speed,
                    distance_m=dist,
                    elapsed_seconds=elapsed,
                )
                for cb in list(self._callbacks):
                    cb(sample)

        self._last[oid] = event
        return sample

    def reset(self, object_id: Optional[str] = None) -> None:
        """Clear stored state for *object_id*, or all objects if None."""
        if object_id is None:
            self._last.clear()
        else:
            self._last.pop(object_id, None)
