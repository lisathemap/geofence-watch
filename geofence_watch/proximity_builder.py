"""Fluent builder for constructing a ProximityStream with fences and callbacks."""
from __future__ import annotations

from typing import Callable, List

from .fence import Geofence
from .proximity_stream import ProximityStream


class ProximityBuilder:
    """Fluent interface for assembling a ProximityStream.

    Example::

        stream = (
            ProximityBuilder()
            .threshold(250.0)
            .fence(my_fence)
            .on_results("logger", print)
            .build()
        )
    """

    def __init__(self) -> None:
        self._threshold_m: float = 500.0
        self._fences: List[Geofence] = []
        self._callbacks: List[tuple] = []

    def threshold(self, metres: float) -> "ProximityBuilder":
        """Set the proximity threshold in metres."""
        if metres <= 0:
            raise ValueError("threshold must be positive.")
        self._threshold_m = metres
        return self

    def fence(self, geofence: Geofence) -> "ProximityBuilder":
        """Register a Geofence with the stream."""
        if not isinstance(geofence, Geofence):
            raise TypeError("Expected a Geofence instance.")
        self._fences.append(geofence)
        return self

    def on_results(self, name: str, fn: Callable) -> "ProximityBuilder":
        """Add a named callback that receives proximity results."""
        if not callable(fn):
            raise TypeError("fn must be callable.")
        self._callbacks.append((name, fn))
        return self

    def build(self) -> ProximityStream:
        """Construct and return the configured ProximityStream."""
        ps = ProximityStream(threshold_m=self._threshold_m)
        for f in self._fences:
            ps.register_fence(f)
        for name, fn in self._callbacks:
            ps.add_callback(name, fn)
        return ps

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ProximityBuilder(threshold_m={self._threshold_m}, "
            f"fences={[f.name for f in self._fences]}, "
            f"callbacks={[n for n, _ in self._callbacks]})"
        )
