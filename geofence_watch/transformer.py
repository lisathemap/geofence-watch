"""Event transformation pipeline for mapping GeofenceEvents to enriched dicts."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from geofence_watch.event import GeofenceEvent


TransformFn = Callable[[GeofenceEvent], Optional[Dict[str, Any]]]


class EventTransformer:
    """Applies an ordered chain of transform functions to GeofenceEvents.

    Each transform receives a ``GeofenceEvent`` and should return either a
    ``dict`` of enriched data or ``None`` to drop the event from the output.

    Example usage::

        t = EventTransformer()
        t.add(lambda e: {"obj": e.object_id, "fence": e.fence_name})
        t.add(lambda e: None if e.event_type.name == "DWELL" else {"obj": e.object_id})
        results = t.run_all(events)
    """

    def __init__(self) -> None:
        self._transforms: List[TransformFn] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add(self, fn: TransformFn) -> None:
        """Append *fn* to the transform chain."""
        if not callable(fn):
            raise TypeError(f"transform must be callable, got {type(fn).__name__!r}")
        self._transforms.append(fn)

    def clear(self) -> None:
        """Remove all registered transforms."""
        self._transforms.clear()

    @property
    def transform_count(self) -> int:
        """Number of transforms currently registered."""
        return len(self._transforms)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def apply(self, event: GeofenceEvent) -> Optional[Dict[str, Any]]:
        """Run *event* through every transform in order.

        Returns the result of the **last** transform that returns a non-None
        value, or ``None`` if any transform drops the event (returns ``None``).
        """
        result: Optional[Dict[str, Any]] = None
        for fn in self._transforms:
            result = fn(event)
            if result is None:
                return None
        return result

    def run_all(
        self, events: List[GeofenceEvent]
    ) -> List[Dict[str, Any]]:
        """Apply the transform chain to every event, dropping ``None`` results."""
        out: List[Dict[str, Any]] = []
        for event in events:
            transformed = self.apply(event)
            if transformed is not None:
                out.append(transformed)
        return out

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventTransformer(transforms={self.transform_count})"
