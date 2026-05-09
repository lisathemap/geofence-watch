"""Drift detector: flags objects whose last known point deviates
beyond a configurable radius from an expected anchor position."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .point import Point
from .proximity import haversine
from .event import GeofenceEvent


@dataclass
class DriftResult:
    """Outcome of a single drift check."""
    object_id: str
    anchor: Point
    current: Point
    distance_m: float
    threshold_m: float
    drifted: bool

    def __repr__(self) -> str:  # pragma: no cover
        status = "DRIFT" if self.drifted else "OK"
        return (
            f"DriftResult({self.object_id!r} {status} "
            f"dist={self.distance_m:.1f}m threshold={self.threshold_m}m)"
        )


class DriftDetector:
    """Track per-object anchor points and emit DriftResult on each update.

    Parameters
    ----------
    threshold_m:
        Default drift threshold in metres.  Individual objects may
        override this via ``set_anchor``.
    """

    def __init__(self, threshold_m: float = 500.0) -> None:
        if threshold_m <= 0:
            raise ValueError("threshold_m must be positive")
        self._default_threshold = threshold_m
        self._anchors: Dict[str, Point] = {}
        self._thresholds: Dict[str, float] = {}
        self._callbacks: List[Callable[[DriftResult], None]] = []

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_anchor(
        self,
        object_id: str,
        anchor: Point,
        threshold_m: Optional[float] = None,
    ) -> None:
        """Register or update the anchor position for *object_id*."""
        self._anchors[object_id] = anchor
        self._thresholds[object_id] = threshold_m if threshold_m is not None else self._default_threshold

    def remove_anchor(self, object_id: str) -> None:
        """Stop tracking *object_id*."""
        self._anchors.pop(object_id, None)
        self._thresholds.pop(object_id, None)

    @property
    def tracked_objects(self) -> List[str]:
        return list(self._anchors.keys())

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def add_callback(self, cb: Callable[[DriftResult], None]) -> None:
        if not callable(cb):
            raise TypeError("callback must be callable")
        self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[DriftResult], None]) -> None:
        self._callbacks.remove(cb)

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def check(self, object_id: str, current: Point) -> Optional[DriftResult]:
        """Check *current* against the stored anchor.  Returns *None* if
        no anchor is registered for *object_id*."""
        if object_id not in self._anchors:
            return None
        anchor = self._anchors[object_id]
        threshold = self._thresholds[object_id]
        dist = haversine(anchor, current)
        result = DriftResult(
            object_id=object_id,
            anchor=anchor,
            current=current,
            distance_m=dist,
            threshold_m=threshold,
            drifted=dist > threshold,
        )
        for cb in self._callbacks:
            cb(result)
        return result

    def ingest(self, event: GeofenceEvent) -> Optional[DriftResult]:
        """Convenience method: extract point from a GeofenceEvent and check."""
        return self.check(event.object_id, event.point)
