"""Stream wrapper that evaluates points against a FenceGroup."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from geofence_watch.fence import Geofence
from geofence_watch.fence_group import FenceGroup
from geofence_watch.point import Point


class FenceGroupStream:
    """Evaluate a stream of :class:`Point` objects against a :class:`FenceGroup`.

    Registered callbacks receive ``(point, matching_fences)`` where
    *matching_fences* is the list of fences that contain the point.
    """

    def __init__(self, group: FenceGroup) -> None:
        if not isinstance(group, FenceGroup):
            raise TypeError(f"Expected FenceGroup, got {type(group).__name__}.")
        self._group = group
        self._callbacks: Dict[str, Callable[[Point, List[Geofence]], None]] = {}

    @property
    def group(self) -> FenceGroup:
        return self._group

    @property
    def callback_names(self) -> List[str]:
        return list(self._callbacks.keys())

    def add_callback(
        self,
        name: str,
        fn: Callable[[Point, List[Geofence]], None],
    ) -> None:
        """Register a named callback."""
        if not name or not name.strip():
            raise ValueError("Callback name must be a non-empty string.")
        if not callable(fn):
            raise TypeError("fn must be callable.")
        self._callbacks[name] = fn

    def remove_callback(self, name: str) -> None:
        """Unregister a callback by name."""
        if name not in self._callbacks:
            raise KeyError(f"No callback named '{name}'.")
        del self._callbacks[name]

    def process(self, point: Point) -> List[Geofence]:
        """Evaluate *point* against the group and invoke all callbacks.

        Returns the list of matching fences.
        """
        if not isinstance(point, Point):
            raise TypeError(f"Expected Point, got {type(point).__name__}.")
        matches = self._group.matching_fences(point)
        for fn in self._callbacks.values():
            fn(point, matches)
        return matches

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"FenceGroupStream(group={self._group.name!r}, "
            f"callbacks={self.callback_names})"
        )
