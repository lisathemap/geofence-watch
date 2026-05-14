"""Stream wrapper that feeds GeofenceEvents into a ClusterDetector."""
from __future__ import annotations

from typing import Callable, Optional

from .cluster_detector import ClusterDetector, ClusterResult
from .event import GeofenceEvent


class ClusterStream:
    """Connects an event source to a :class:`ClusterDetector`.

    Parameters
    ----------
    detector:
        Optional pre-configured detector; a default one is created when
        *min_size* is provided.
    min_size:
        Forwarded to a newly created :class:`ClusterDetector` when no
        *detector* is given.  Ignored if *detector* is supplied.
    """

    def __init__(
        self,
        detector: Optional[ClusterDetector] = None,
        *,
        min_size: int = 2,
    ) -> None:
        if detector is not None and not isinstance(detector, ClusterDetector):
            raise TypeError("detector must be a ClusterDetector instance")
        self._detector = detector if detector is not None else ClusterDetector(min_size=min_size)

    @property
    def detector(self) -> ClusterDetector:
        return self._detector

    def callback_names(self):
        return self._detector.callback_names()

    def add_callback(self, name: str, fn: Callable[[ClusterResult], None]) -> None:
        self._detector.add_callback(name, fn)

    def remove_callback(self, name: str) -> None:
        self._detector.remove_callback(name)

    def process(self, event: GeofenceEvent) -> Optional[ClusterResult]:
        """Feed *event* into the detector and return any cluster result."""
        return self._detector.ingest(event)
