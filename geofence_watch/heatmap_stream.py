"""Streaming wrapper that feeds a live event source into HeatmapBuilder."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from .event import GeofenceEvent
from .heatmap import HeatmapBuilder


class HeatmapStream:
    """Wraps a HeatmapBuilder and wires it into a callback-based pipeline.

    Usage::

        stream = HeatmapStream()
        stream.add_callback(lambda hm: print(hm.top_fences()))
        stream.feed(event)
    """

    def __init__(self, builder: Optional[HeatmapBuilder] = None) -> None:
        if builder is not None and not isinstance(builder, HeatmapBuilder):
            raise TypeError("builder must be a HeatmapBuilder instance")
        self._builder: HeatmapBuilder = builder or HeatmapBuilder()
        self._callbacks: Dict[str, Callable[[HeatmapBuilder], None]] = {}

    @property
    def builder(self) -> HeatmapBuilder:
        """The underlying HeatmapBuilder."""
        return self._builder

    @property
    def callback_names(self) -> List[str]:
        return list(self._callbacks)

    def add_callback(self, name: str, fn: Callable[[HeatmapBuilder], None]) -> None:
        """Register a callback invoked after every ingested event."""
        if not callable(fn):
            raise TypeError("fn must be callable")
        if not name:
            raise ValueError("name must be a non-empty string")
        self._callbacks[name] = fn

    def remove_callback(self, name: str) -> None:
        """Unregister a previously added callback."""
        self._callbacks.pop(name, None)

    def feed(self, event: GeofenceEvent) -> None:
        """Ingest *event* into the builder and notify all callbacks."""
        self._builder.ingest(event)
        for fn in self._callbacks.values():
            fn(self._builder)

    def reset(self) -> None:
        """Delegate reset to the underlying builder."""
        self._builder.reset()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"HeatmapStream(callbacks={list(self._callbacks)}, "
            f"builder={self._builder!r})"
        )
