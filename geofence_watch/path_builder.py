"""Fluent builder for constructing a PathStream with common options."""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from .path_tracker import PathRecord, PathTracker
from .path_stream import PathStream


class PathBuilder:
    """Fluent builder for PathStream.

    Example::

        stream = (
            PathBuilder()
            .max_length(10)
            .only_objects("truck-1", "truck-2")
            .on_update(lambda r: print(r))
            .build()
        )
    """

    def __init__(self) -> None:
        self._max: Optional[int] = None
        self._objects: Optional[Tuple[str, ...]] = None
        self._callbacks: List[Tuple[str, Callable[[PathRecord], None]]] = []
        self._cb_counter = 0

    def max_length(self, n: int) -> "PathBuilder":
        """Cap the recorded path to the *n* most recent fence entries."""
        if not isinstance(n, int) or n < 1:
            raise ValueError("max_length must be a positive integer")
        self._max = n
        return self

    def only_objects(self, *object_ids: str) -> "PathBuilder":
        """Restrict tracking to the specified object IDs."""
        if not object_ids:
            raise ValueError("Provide at least one object_id")
        self._objects = tuple(object_ids)
        return self

    def on_update(self, cb: Callable[[PathRecord], None]) -> "PathBuilder":
        """Register a callback invoked whenever a path record is updated."""
        if not callable(cb):
            raise TypeError("cb must be callable")
        name = f"_builder_cb_{self._cb_counter}"
        self._cb_counter += 1
        self._callbacks.append((name, cb))
        return self

    def build(self) -> PathStream:
        """Construct and return the configured PathStream."""
        tracker = PathTracker(
            max_path_length=self._max,
            track_objects=self._objects,
        )
        stream = PathStream(tracker=tracker)
        for name, cb in self._callbacks:
            stream.add_callback(name, cb)
        return stream
