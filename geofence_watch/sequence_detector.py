"""Detect ordered sequences of geofence events for a given object."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .event import EventType, GeofenceEvent


@dataclass
class SequenceMatch:
    """Emitted when a full sequence has been matched for an object."""

    object_id: str
    pattern: Tuple[Tuple[str, EventType], ...]
    events: List[GeofenceEvent] = field(default_factory=list)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SequenceMatch(object_id={self.object_id!r}, "
            f"steps={len(self.pattern)})"
        )


class SequenceDetector:
    """Detect ordered (fence, event_type) patterns across an event stream.

    Parameters
    ----------
    pattern:
        Ordered list of ``(fence_name, EventType)`` tuples that must be
        observed in sequence for the same *object_id* to trigger a match.
    reset_on_mismatch:
        When *True* (default) a step that does not match the next expected
        position resets progress for that object back to zero.
    """

    def __init__(
        self,
        pattern: List[Tuple[str, EventType]],
        *,
        reset_on_mismatch: bool = True,
    ) -> None:
        if not pattern:
            raise ValueError("pattern must contain at least one step")
        self._pattern: Tuple[Tuple[str, EventType], ...] = tuple(pattern)
        self._reset_on_mismatch = reset_on_mismatch
        self._progress: dict[str, int] = {}
        self._buffers: dict[str, List[GeofenceEvent]] = {}
        self._callbacks: List[Callable[[SequenceMatch], None]] = []

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def pattern(self) -> Tuple[Tuple[str, EventType], ...]:
        return self._pattern

    def add_callback(self, cb: Callable[[SequenceMatch], None]) -> None:
        if not callable(cb):
            raise TypeError("callback must be callable")
        self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[SequenceMatch], None]) -> None:
        self._callbacks.remove(cb)

    def progress(self, object_id: str) -> int:
        """Return how many steps have been matched so far for *object_id*."""
        return self._progress.get(object_id, 0)

    def reset(self, object_id: Optional[str] = None) -> None:
        """Reset progress; pass *None* to reset all objects."""
        if object_id is None:
            self._progress.clear()
            self._buffers.clear()
        else:
            self._progress.pop(object_id, None)
            self._buffers.pop(object_id, None)

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def feed(self, event: GeofenceEvent) -> None:
        """Feed one event into the detector."""
        oid = event.object_id
        step = self._progress.get(oid, 0)
        expected_fence, expected_type = self._pattern[step]

        if event.fence_name == expected_fence and event.event_type == expected_type:
            self._buffers.setdefault(oid, []).append(event)
            step += 1
            if step == len(self._pattern):
                match = SequenceMatch(
                    object_id=oid,
                    pattern=self._pattern,
                    events=list(self._buffers[oid]),
                )
                self.reset(oid)
                for cb in list(self._callbacks):
                    cb(match)
            else:
                self._progress[oid] = step
        elif self._reset_on_mismatch:
            self.reset(oid)
