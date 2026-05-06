"""Stream wrapper that emits proximity results for every ingested point."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from .point import Point
from .fence import Geofence
from .proximity import ProximityMonitor, ProximityResult


CallbackFn = Callable[[List[ProximityResult]], None]


class ProximityStream:
    """Wraps ProximityMonitor and fans out results to registered callbacks."""

    def __init__(self, threshold_m: float = 500.0) -> None:
        self._monitor = ProximityMonitor(threshold_m=threshold_m)
        self._callbacks: Dict[str, CallbackFn] = {}

    @property
    def monitor(self) -> ProximityMonitor:
        return self._monitor

    # --- fence management passthrough ---

    def register_fence(self, fence: Geofence) -> None:
        self._monitor.register(fence)

    def unregister_fence(self, name: str) -> None:
        self._monitor.unregister(name)

    # --- callback management ---

    def add_callback(self, name: str, fn: CallbackFn) -> None:
        if not callable(fn):
            raise TypeError("fn must be callable.")
        self._callbacks[name] = fn

    def remove_callback(self, name: str) -> None:
        self._callbacks.pop(name, None)

    @property
    def callback_names(self) -> list:
        return list(self._callbacks.keys())

    # --- processing ---

    def process(self, object_id: str, point: Point) -> List[ProximityResult]:
        """Compute proximity results and invoke all callbacks."""
        results = self._monitor.check(object_id, point)
        for fn in self._callbacks.values():
            fn(results)
        return results

    def nearest(self, object_id: str, point: Point) -> Optional[ProximityResult]:
        """Return only the nearest result without firing callbacks."""
        return self._monitor.nearest(object_id, point)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ProximityStream(threshold_m={self._monitor.threshold_m}, "
            f"fences={self._monitor.fence_names}, "
            f"callbacks={self.callback_names})"
        )
