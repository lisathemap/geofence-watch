"""Stream wrapper that feeds GeofenceEvents into a SequenceDetector."""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from .event import EventType, GeofenceEvent
from .sequence_detector import SequenceDetector, SequenceMatch


class SequenceStream:
    """Combine a :class:`SequenceDetector` with a live event feed.

    Parameters
    ----------
    pattern:
        Ordered list of ``(fence_name, EventType)`` tuples.
    reset_on_mismatch:
        Forwarded to the underlying :class:`SequenceDetector`.
    """

    def __init__(
        self,
        pattern: List[Tuple[str, EventType]],
        *,
        reset_on_mismatch: bool = True,
        detector: Optional[SequenceDetector] = None,
    ) -> None:
        if detector is not None:
            if not isinstance(detector, SequenceDetector):
                raise TypeError("detector must be a SequenceDetector instance")
            self._detector = detector
        else:
            self._detector = SequenceDetector(
                pattern, reset_on_mismatch=reset_on_mismatch
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def detector(self) -> SequenceDetector:
        return self._detector

    def callback_names(self) -> List[str]:
        return [getattr(cb, "__name__", repr(cb)) for cb in self._detector._callbacks]

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------

    def add_callback(self, cb: Callable[[SequenceMatch], None]) -> None:
        self._detector.add_callback(cb)

    def remove_callback(self, cb: Callable[[SequenceMatch], None]) -> None:
        self._detector.remove_callback(cb)

    def process(self, event: GeofenceEvent) -> None:
        """Feed *event* into the underlying detector."""
        self._detector.feed(event)

    def progress(self, object_id: str) -> int:
        return self._detector.progress(object_id)

    def reset(self, object_id: Optional[str] = None) -> None:
        self._detector.reset(object_id)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SequenceStream(steps={len(self._detector.pattern)}, "
            f"callbacks={len(self._detector._callbacks)})"
        )
