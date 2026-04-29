"""Core geofence containment checker using the ray-casting algorithm."""

from __future__ import annotations

from typing import Iterator

from geofence_watch.fence import Geofence
from geofence_watch.point import Point


class GeofenceChecker:
    """Evaluates points against one or more registered geofences."""

    def __init__(self) -> None:
        self._fences: dict[str, Geofence] = {}

    def register(self, fence: Geofence) -> None:
        """Register a geofence under its name."""
        self._fences[fence.name] = fence

    def unregister(self, name: str) -> None:
        """Remove a geofence by name."""
        self._fences.pop(name, None)

    @property
    def fence_names(self) -> list[str]:
        return list(self._fences.keys())

    def contains(self, fence: Geofence, point: Point) -> bool:
        """Return True if *point* lies inside *fence* using ray-casting."""
        lon, lat = point.longitude, point.latitude
        ring = fence.ring
        inside = False
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def check_point(self, point: Point) -> dict[str, bool]:
        """Check *point* against all registered fences. Returns {fence_name: inside}."""
        return {name: self.contains(fence, point) for name, fence in self._fences.items()}

    def matching_fences(self, point: Point) -> Iterator[str]:
        """Yield names of fences that contain *point*."""
        for name, fence in self._fences.items():
            if self.contains(fence, point):
                yield name
