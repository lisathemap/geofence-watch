"""Fluent builder for constructing :class:`~geofence_watch.pipeline.EventPipeline` instances."""

from __future__ import annotations

from typing import Callable, Optional

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.pipeline import EventPipeline, ProcessorFn


class PipelineBuilder:
    """Fluent helper that assembles an :class:`EventPipeline` step by step.

    Example::

        pipeline = (
            PipelineBuilder()
            .filter_by_type(EventType.ENTER)
            .filter_by_fence("zone-a", "zone-b")
            .add_stage(my_transform)
            .on_output(my_callback)
            .build()
        )
    """

    def __init__(self) -> None:
        self._stages: list[ProcessorFn] = []
        self._callbacks: list[Callable[[GeofenceEvent], None]] = []

    # ------------------------------------------------------------------
    # Built-in filter helpers
    # ------------------------------------------------------------------

    def filter_by_type(self, *event_types: EventType) -> "PipelineBuilder":
        """Drop events whose type is not in *event_types*."""
        allowed = set(event_types)

        def _stage(event: GeofenceEvent) -> Optional[GeofenceEvent]:
            return event if event.event_type in allowed else None

        self._stages.append(_stage)
        return self

    def filter_by_fence(self, *fence_names: str) -> "PipelineBuilder":
        """Drop events that do not belong to one of *fence_names*."""
        allowed = set(fence_names)

        def _stage(event: GeofenceEvent) -> Optional[GeofenceEvent]:
            return event if event.fence_name in allowed else None

        self._stages.append(_stage)
        return self

    def filter_by_object(self, *object_ids: str) -> "PipelineBuilder":
        """Drop events whose object_id is not in *object_ids*."""
        allowed = set(object_ids)

        def _stage(event: GeofenceEvent) -> Optional[GeofenceEvent]:
            return event if event.object_id in allowed else None

        self._stages.append(_stage)
        return self

    # ------------------------------------------------------------------
    # Generic stage / callback registration
    # ------------------------------------------------------------------

    def add_stage(self, fn: ProcessorFn) -> "PipelineBuilder":
        """Append a custom processing stage."""
        if not callable(fn):
            raise TypeError(f"Stage must be callable, got {type(fn).__name__!r}")
        self._stages.append(fn)
        return self

    def on_output(self, fn: Callable[[GeofenceEvent], None]) -> "PipelineBuilder":
        """Register *fn* as an output callback on the finished pipeline."""
        if not callable(fn):
            raise TypeError(f"Callback must be callable, got {type(fn).__name__!r}")
        self._callbacks.append(fn)
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> EventPipeline:
        """Construct and return the configured :class:`EventPipeline`."""
        pipe = EventPipeline()
        for stage in self._stages:
            pipe.add_stage(stage)
        for cb in self._callbacks:
            pipe.add_callback(cb)
        return pipe

    def __repr__(self) -> str:  # pragma: no cover
        return f"PipelineBuilder(stages={len(self._stages)}, callbacks={len(self._callbacks)})"
