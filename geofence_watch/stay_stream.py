"""Stream wrapper that pipes GeofenceEvents through StayDetector."""
from __future__ import annotations

from typing import Callable, Optional, Tuple

from .event import GeofenceEvent
from .stay_detector import StayDetector, StayResult


class StayStream:
    """Wraps a :class:`StayDetector` and processes events from a feed."""

    def __init__(
        self,
        detector: Optional[StayDetector] = None,
        *,
        min_seconds: float = 60.0,
    ) -> None:
        if detector is not None and not isinstance(detector, StayDetector):
            raise TypeError("detector must be a StayDetector instance")
        self._detector = detector if detector is not None else StayDetector(min_seconds=min_seconds)

    @property
    def detector(self) -> StayDetector:
        return self._detector

    @property
    def callback_names(self) -> Tuple[str, ...]:
        return self._detector.callback_names

    def add_callback(self, name: str, fn: Callable[[StayResult], None]) -> None:
        self._detector.add_callback(name, fn)

    def remove_callback(self, name: str) -> None:
        self._detector.remove_callback(name)

    def process(self, event: GeofenceEvent) -> Optional[StayResult]:
        """Feed *event* into the detector and return a result if a stay was detected."""
        if not isinstance(event, GeofenceEvent):
            raise TypeError("event must be a GeofenceEvent")
        return self._detector.ingest(event)

    def reset(self) -> None:
        self._detector.reset()
