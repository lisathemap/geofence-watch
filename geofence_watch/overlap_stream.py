"""Stream wrapper that feeds GeofenceEvents into an OverlapDetector."""
from __future__ import annotations

from typing import Callable, List, Optional

from .event import GeofenceEvent
from .overlap_detector import OverlapDetector, OverlapResult


class OverlapStream:
    """Wraps an OverlapDetector and exposes a stream-friendly interface."""

    def __init__(self, detector: Optional[OverlapDetector] = None) -> None:
        self._detector = detector if detector is not None else OverlapDetector()

    @property
    def detector(self) -> OverlapDetector:
        return self._detector

    def callback_names(self) -> List[str]:
        return self._detector.callback_names()

    def add_callback(self, name: str, fn: Callable[[OverlapResult], None]) -> None:
        self._detector.add_callback(name, fn)

    def remove_callback(self, name: str) -> None:
        self._detector.remove_callback(name)

    def process(self, event: GeofenceEvent) -> Optional[OverlapResult]:
        """Ingest a single event and return an OverlapResult if applicable."""
        return self._detector.ingest(event)

    def active_fences(self, object_id: str):
        return self._detector.active_fences(object_id)

    def reset(self, object_id: Optional[str] = None) -> None:
        self._detector.reset(object_id)
