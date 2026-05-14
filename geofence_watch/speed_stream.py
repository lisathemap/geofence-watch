"""Stream wrapper that wires GeofenceStream output into SpeedEstimator."""
from __future__ import annotations

from typing import Callable, List, Optional

from .event import GeofenceEvent
from .speed_estimator import SpeedEstimator, SpeedSample


class SpeedStream:
    """Connects a raw event source to a :class:`SpeedEstimator`.

    Usage::

        ss = SpeedStream()
        ss.add_callback(lambda s: print(s.speed_kph))
        # feed events from a GeofenceStream or any other source
        ss.process(event)
    """

    def __init__(
        self,
        estimator: Optional[SpeedEstimator] = None,
        min_elapsed_seconds: float = 0.1,
    ) -> None:
        if estimator is not None and not isinstance(estimator, SpeedEstimator):
            raise TypeError("estimator must be a SpeedEstimator instance")
        self._estimator = estimator or SpeedEstimator(
            min_elapsed_seconds=min_elapsed_seconds
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def estimator(self) -> SpeedEstimator:
        return self._estimator

    @property
    def callback_names(self) -> List[str]:
        return [cb.__name__ for cb in self._estimator._callbacks]

    # ------------------------------------------------------------------
    # Callback management (delegates to estimator)
    # ------------------------------------------------------------------

    def add_callback(self, fn: Callable[[SpeedSample], None]) -> None:
        self._estimator.add_callback(fn)

    def remove_callback(self, fn: Callable[[SpeedSample], None]) -> None:
        self._estimator.remove_callback(fn)

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self, event: GeofenceEvent) -> Optional[SpeedSample]:
        """Feed *event* through the estimator and return any SpeedSample."""
        return self._estimator.ingest(event)
