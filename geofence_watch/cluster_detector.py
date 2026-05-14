"""Cluster detector: groups objects by proximity within a fence."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .event import GeofenceEvent, EventType
from .proximity import haversine


@dataclass
class ClusterResult:
    """Snapshot of a detected cluster inside a fence."""

    fence_name: str
    object_ids: Tuple[str, ...]
    centroid_lat: float
    centroid_lon: float

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ClusterResult(fence={self.fence_name!r}, "
            f"objects={self.object_ids}, "
            f"centroid=({self.centroid_lat:.5f}, {self.centroid_lon:.5f}))"
        )

    @property
    def size(self) -> int:
        return len(self.object_ids)


class ClusterDetector:
    """Tracks which objects are currently inside each fence and emits
    ClusterResult when the number of co-located objects meets *min_size*.
    """

    def __init__(self, min_size: int = 2) -> None:
        if min_size < 2:
            raise ValueError("min_size must be >= 2")
        self._min_size = min_size
        # fence_name -> {object_id -> (lat, lon)}
        self._positions: Dict[str, Dict[str, Tuple[float, float]]] = {}
        self._callbacks: Dict[str, Callable[[ClusterResult], None]] = {}

    @property
    def min_size(self) -> int:
        return self._min_size

    def callback_names(self) -> Tuple[str, ...]:
        return tuple(self._callbacks)

    def add_callback(self, name: str, fn: Callable[[ClusterResult], None]) -> None:
        if not callable(fn):
            raise TypeError("fn must be callable")
        self._callbacks[name] = fn

    def remove_callback(self, name: str) -> None:
        self._callbacks.pop(name, None)

    def ingest(self, event: GeofenceEvent) -> Optional[ClusterResult]:
        fence = event.fence_name
        obj = event.object_id
        lat = event.point.lat
        lon = event.point.lon

        if fence not in self._positions:
            self._positions[fence] = {}

        if event.event_type == EventType.ENTER:
            self._positions[fence][obj] = (lat, lon)
        elif event.event_type == EventType.EXIT:
            self._positions[fence].pop(obj, None)

        members = self._positions[fence]
        if len(members) < self._min_size:
            return None

        lats = [p[0] for p in members.values()]
        lons = [p[1] for p in members.values()]
        c_lat = sum(lats) / len(lats)
        c_lon = sum(lons) / len(lons)

        result = ClusterResult(
            fence_name=fence,
            object_ids=tuple(sorted(members)),
            centroid_lat=c_lat,
            centroid_lon=c_lon,
        )
        for cb in self._callbacks.values():
            cb(result)
        return result
