"""DriftStream: wires a GeofenceStream to a DriftDetector so that
every processed coordinate update is automatically drift-checked.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from .drift_detector import DriftDetector, DriftResult
from .event import GeofenceEvent
from .point import Point


class DriftStream:
    """Feed GeofenceEvents into a DriftDetector and broadcast results.

    Parameters
    ----------
    detector:
        A pre-configured :class:`DriftDetector`.  If *None* a default
        instance (500 m threshold) is created automatically.
    """

    def __init__(self, detector: Optional[DriftDetector] = None) -> None:
        self._detector = detector if detector is not None else DriftDetector()
        self._callbacks: List[Callable[[DriftResult], None]] = []
        # Forward detector results to our own callback list
        self._detector.add_callback(self._broadcast)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def detector(self) -> DriftDetector:
        return self._detector

    @property
    def callback_names(self) -> List[str]:
        return [cb.__name__ for cb in self._callbacks]

    # ------------------------------------------------------------------
    # Anchor management (delegated)
    # ------------------------------------------------------------------

    def set_anchor(
        self,
        object_id: str,
        anchor: Point,
        threshold_m: Optional[float] = None,
    ) -> None:
        self._detector.set_anchor(object_id, anchor, threshold_m)

    def remove_anchor(self, object_id: str) -> None:
        self._detector.remove_anchor(object_id)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def add_callback(self, cb: Callable[[DriftResult], None]) -> None:
        if not callable(cb):
            raise TypeError("callback must be callable")
        self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[DriftResult], None]) -> None:
        self._callbacks.remove(cb)

    def _broadcast(self, result: DriftResult) -> None:
        for cb in self._callbacks:
            cb(result)

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def process(self, event: GeofenceEvent) -> Optional[DriftResult]:
        """Process a single GeofenceEvent; returns the DriftResult or None."""
        return self._detector.ingest(event)
