"""Group multiple Geofence instances under a named collection."""
from __future__ import annotations

from typing import Dict, Iterable, Iterator, List

from geofence_watch.fence import Geofence
from geofence_watch.point import Point


class FenceGroup:
    """A named collection of :class:`Geofence` objects.

    Useful for logical groupings such as "restricted zones" or
    "delivery regions" that should be queried together.
    """

    def __init__(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("FenceGroup name must be a non-empty string.")
        self._name: str = name
        self._fences: Dict[str, Geofence] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def fence_names(self) -> List[str]:
        return list(self._fences.keys())

    def add(self, fence: Geofence) -> None:
        """Add a fence to the group."""
        if not isinstance(fence, Geofence):
            raise TypeError(f"Expected Geofence, got {type(fence).__name__}.")
        self._fences[fence.name] = fence

    def remove(self, name: str) -> None:
        """Remove a fence by name; raises KeyError if not found."""
        if name not in self._fences:
            raise KeyError(f"Fence '{name}' not in group '{self._name}'.")
        del self._fences[name]

    def get(self, name: str) -> Geofence:
        """Return a fence by name."""
        if name not in self._fences:
            raise KeyError(f"Fence '{name}' not in group '{self._name}'.")
        return self._fences[name]

    def contains_any(self, point: Point) -> bool:
        """Return True if the point is inside *any* fence in the group."""
        return any(f.contains(point) for f in self._fences.values())

    def contains_all(self, point: Point) -> bool:
        """Return True if the point is inside *every* fence in the group."""
        if not self._fences:
            return False
        return all(f.contains(point) for f in self._fences.values())

    def matching_fences(self, point: Point) -> List[Geofence]:
        """Return all fences that contain the given point."""
        return [f for f in self._fences.values() if f.contains(point)]

    def __iter__(self) -> Iterator[Geofence]:
        return iter(self._fences.values())

    def __len__(self) -> int:
        return len(self._fences)

    def __repr__(self) -> str:  # pragma: no cover
        return f"FenceGroup(name={self._name!r}, fences={self.fence_names})"
