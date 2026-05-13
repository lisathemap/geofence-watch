"""Stream wrapper that feeds geofence events through a CorridorDetector
and dispatches CorridorResult objects to registered callbacks."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence

from .corridor_detector import CorridorDetector, CorridorResult
from .event import GeofenceEvent


class CorridorStream:
    """Connects a :class:`CorridorDetector` to a live event feed.

    Parameters
    ----------
    name:
        Corridor name forwarded to the underlying detector.
    steps:
        Ordered fence names that form the corridor.
    strict:
        Passed through to :class:`CorridorDetector`.
    detector:
        Supply a pre-built detector instead of constructing one.
    """

    def __init__(
        self,
        name: str = "",
        steps: Sequence[str] = (),
        *,
        strict: bool = True,
        detector: Optional[CorridorDetector] = None,
    ) -> None:
        if detector is not None:
            if not isinstance(detector, CorridorDetector):
                raise TypeError("detector must be a CorridorDetector instance")
            self._detector = detector
        else:
            self._detector = CorridorDetector(name, steps, strict=strict)

        self._callbacks: Dict[str, Callable[[CorridorResult], None]] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def detector(self) -> CorridorDetector:
        return self._detector

    @property
    def callback_names(self) -> List[str]:
        return list(self._callbacks)

    # ------------------------------------------------------------------
    # Callback management
    # ------------------------------------------------------------------

    def add_callback(
        self, name: str, fn: Callable[[CorridorResult], None]
    ) -> None:
        if not name:
            raise ValueError("callback name must be non-empty")
        if not callable(fn):
            raise TypeError("fn must be callable")
        self._callbacks[name] = fn

    def remove_callback(self, name: str) -> None:
        self._callbacks.pop(name, None)

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self, event: GeofenceEvent) -> Optional[CorridorResult]:
        """Feed *event* into the detector; fire callbacks on a result."""
        result = self._detector.ingest(event)
        if result is not None:
            for fn in list(self._callbacks.values()):
                fn(result)
        return result
