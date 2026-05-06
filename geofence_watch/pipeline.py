"""Composable event pipeline for chaining geofence-watch processors."""

from __future__ import annotations

from typing import Callable, List, Optional

from geofence_watch.event import GeofenceEvent


ProcessorFn = Callable[[GeofenceEvent], Optional[GeofenceEvent]]


class EventPipeline:
    """Chain multiple event processors into a single callable pipeline.

    Each stage is a callable that accepts a :class:`GeofenceEvent` and returns
    either a (possibly modified) :class:`GeofenceEvent` or ``None``.  When a
    stage returns ``None`` the event is dropped and no further stages are
    executed.

    Example usage::

        pipeline = EventPipeline()
        pipeline.add_stage(my_filter_fn)
        pipeline.add_stage(my_transform_fn)
        result = pipeline.process(event)  # None if dropped
    """

    def __init__(self) -> None:
        self._stages: List[ProcessorFn] = []
        self._callbacks: List[Callable[[GeofenceEvent], None]] = []

    # ------------------------------------------------------------------
    # Stage management
    # ------------------------------------------------------------------

    def add_stage(self, fn: ProcessorFn) -> None:
        """Append *fn* as the next stage in the pipeline."""
        if not callable(fn):
            raise TypeError(f"Stage must be callable, got {type(fn).__name__!r}")
        self._stages.append(fn)

    def remove_stage(self, fn: ProcessorFn) -> None:
        """Remove the first occurrence of *fn* from the pipeline."""
        try:
            self._stages.remove(fn)
        except ValueError:
            raise KeyError(f"Stage {fn!r} is not registered in this pipeline")

    @property
    def stage_count(self) -> int:
        """Number of stages currently in the pipeline."""
        return len(self._stages)

    # ------------------------------------------------------------------
    # Output callbacks
    # ------------------------------------------------------------------

    def add_callback(self, fn: Callable[[GeofenceEvent], None]) -> None:
        """Register *fn* to be called with events that survive all stages."""
        if not callable(fn):
            raise TypeError(f"Callback must be callable, got {type(fn).__name__!r}")
        self._callbacks.append(fn)

    def remove_callback(self, fn: Callable[[GeofenceEvent], None]) -> None:
        """Unregister a previously added callback."""
        try:
            self._callbacks.remove(fn)
        except ValueError:
            raise KeyError(f"Callback {fn!r} is not registered in this pipeline")

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self, event: GeofenceEvent) -> Optional[GeofenceEvent]:
        """Run *event* through every stage and notify callbacks if it survives.

        Returns the (possibly transformed) event, or ``None`` if it was
        dropped by a stage.
        """
        current: Optional[GeofenceEvent] = event
        for stage in self._stages:
            current = stage(current)
            if current is None:
                return None
        for cb in self._callbacks:
            cb(current)
        return current

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventPipeline(stages={self.stage_count})"
