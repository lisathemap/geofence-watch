"""Proximity detection: measure distance between a Point and Geofence centroid."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

from .point import Point
from .fence import Geofence


_EARTH_RADIUS_M = 6_371_000.0


def haversine(a: Point, b: Point) -> float:
    """Return the great-circle distance in metres between two Points."""
    lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
    lat2, lon2 = math.radians(b.lat), math.radians(b.lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))


def _centroid(fence: Geofence) -> Point:
    """Return the arithmetic centroid of a Geofence's outer ring."""
    coords = fence.ring
    if not coords:
        raise ValueError(f"Geofence '{fence.name}' has an empty ring.")
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return Point(lon=sum(lons) / len(lons), lat=sum(lats) / len(lats))


@dataclass
class ProximityResult:
    """Distance measurement from a point to a named fence centroid."""

    object_id: str
    fence_name: str
    distance_m: float
    within_threshold: bool

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ProximityResult(object_id={self.object_id!r}, "
            f"fence={self.fence_name!r}, "
            f"distance_m={self.distance_m:.1f}, "
            f"within={self.within_threshold})"
        )


class ProximityMonitor:
    """Check how close objects are to registered geofence centroids."""

    def __init__(self, threshold_m: float = 500.0) -> None:
        if threshold_m <= 0:
            raise ValueError("threshold_m must be positive.")
        self._threshold_m = threshold_m
        self._fences: Dict[str, Geofence] = {}

    @property
    def threshold_m(self) -> float:
        return self._threshold_m

    def register(self, fence: Geofence) -> None:
        self._fences[fence.name] = fence

    def unregister(self, name: str) -> None:
        self._fences.pop(name, None)

    @property
    def fence_names(self) -> list:
        return list(self._fences.keys())

    def check(self, object_id: str, point: Point) -> list:
        """Return a ProximityResult for every registered fence."""
        results = []
        for name, fence in self._fences.items():
            centroid = _centroid(fence)
            dist = haversine(point, centroid)
            results.append(
                ProximityResult(
                    object_id=object_id,
                    fence_name=name,
                    distance_m=dist,
                    within_threshold=dist <= self._threshold_m,
                )
            )
        return results

    def nearest(self, object_id: str, point: Point) -> Optional[ProximityResult]:
        """Return the ProximityResult for the closest fence, or None."""
        results = self.check(object_id, point)
        if not results:
            return None
        return min(results, key=lambda r: r.distance_m)
