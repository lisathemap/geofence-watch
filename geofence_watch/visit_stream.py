"""Stream wrapper that feeds events into a VisitCounter and fires callbacks."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from .event import GeofenceEvent
from .visit_counter import VisitCounter


class VisitStream:
    """Wraps a :class:`VisitCounter` and notifies registered callbacks after
    each ingested ENTER event.

    Callbacks receive ``(event, counter)`` so downstream code can inspect the
    updated counts immediately.
    """

    def __init__(self, counter: Optional[VisitCounter] = None) -> None:
        self._counter = counter if counter is not None else VisitCounter()
        self._callbacks: Dict[str, Callable[[GeofenceEvent, VisitCounter], None]] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def counter(self) -> VisitCounter:
        return self._counter

    @property
    def callback_names(self) -> Tuple[str, ...]:
        return tuple(self._callbacks)

    # ------------------------------------------------------------------
    # Callback management
    # ------------------------------------------------------------------

    def add_callback(
        self,
        name: str,
        fn: Callable[[GeofenceEvent, VisitCounter], None],
    ) -> None:
        if not callable(fn):
            raise TypeError(f"callback must be callable, got {type(fn)}")
        if not name:
            raise ValueError("callback name must be a non-empty string")
        self._callbacks[name] = fn

    def remove_callback(self, name: str) -> None:
        self._callbacks.pop(name, None)

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self, event: GeofenceEvent) -> None:
        """Ingest *event* and fire callbacks if it was an ENTER event."""
        from .event import EventType
        self._counter.ingest(event)
        if event.event_type is EventType.ENTER:
            for fn in list(self._callbacks.values()):
                fn(event, self._counter)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"VisitStream(callbacks={list(self._callbacks)}, "
            f"counter={self._counter})"
        )
