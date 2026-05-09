"""Fluent builder for constructing a HeatmapStream with optional filtering."""
from __future__ import annotations

from typing import Callable, List, Optional

from .event import EventType, GeofenceEvent
from .heatmap import HeatmapBuilder
from .heatmap_stream import HeatmapStream


class HeatmapPipelineBuilder:
    """Fluent builder that wires filtering and callbacks onto a HeatmapStream.

    Example::

        stream = (
            HeatmapPipelineBuilder()
            .filter_fences(["zone_a", "zone_b"])
            .on_update(lambda hm: print(hm.top_fences(3)))
            .build()
        )
    """

    def __init__(self) -> None:
        self._fence_filter: Optional[List[str]] = None
        self._object_filter: Optional[List[str]] = None
        self._callbacks: List[tuple[str, Callable[[HeatmapBuilder], None]]] = []
        self._builder: Optional[HeatmapBuilder] = None

    def filter_fences(self, fence_names: List[str]) -> "HeatmapPipelineBuilder":
        """Only ingest events belonging to the specified fences."""
        if not fence_names:
            raise ValueError("fence_names must be a non-empty list")
        self._fence_filter = list(fence_names)
        return self

    def filter_objects(self, object_ids: List[str]) -> "HeatmapPipelineBuilder":
        """Only ingest events for the specified object IDs."""
        if not object_ids:
            raise ValueError("object_ids must be a non-empty list")
        self._object_filter = list(object_ids)
        return self

    def on_update(
        self,
        fn: Callable[[HeatmapBuilder], None],
        name: Optional[str] = None,
    ) -> "HeatmapPipelineBuilder":
        """Register a callback to be invoked after each accepted event."""
        if not callable(fn):
            raise TypeError("fn must be callable")
        cb_name = name or f"_cb_{len(self._callbacks)}"
        self._callbacks.append((cb_name, fn))
        return self

    def with_builder(self, builder: HeatmapBuilder) -> "HeatmapPipelineBuilder":
        """Provide a pre-existing HeatmapBuilder instead of creating a new one."""
        if not isinstance(builder, HeatmapBuilder):
            raise TypeError("builder must be a HeatmapBuilder")
        self._builder = builder
        return self

    def build(self) -> HeatmapStream:
        """Construct and return the configured HeatmapStream."""
        base_builder = self._builder or HeatmapBuilder()
        stream = HeatmapStream(builder=base_builder)

        fence_filter = self._fence_filter
        object_filter = self._object_filter

        if fence_filter is not None or object_filter is not None:
            # Wrap each registered callback with a pre-filter on the raw event.
            original_feed = stream.feed

            def filtered_feed(event: GeofenceEvent) -> None:
                if fence_filter and event.fence_name not in fence_filter:
                    return
                if object_filter and event.object_id not in object_filter:
                    return
                original_feed(event)

            stream.feed = filtered_feed  # type: ignore[method-assign]

        for cb_name, fn in self._callbacks:
            stream.add_callback(cb_name, fn)

        return stream
