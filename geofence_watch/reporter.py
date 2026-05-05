"""Summary reporter for geofence activity over a history store."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .event import EventType, GeofenceEvent
from .history import ObjectHistory


@dataclass
class FenceSummary:
    """Aggregated statistics for a single (object_id, fence_name) pair."""

    object_id: str
    fence_name: str
    enter_count: int = 0
    exit_count: int = 0
    last_event: Optional[GeofenceEvent] = None

    @property
    def is_inside(self) -> bool:
        """Return True if the most recent event was an ENTER."""
        return self.last_event is not None and self.last_event.event_type == EventType.ENTER

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"FenceSummary(object_id={self.object_id!r}, fence={self.fence_name!r}, "
            f"enters={self.enter_count}, exits={self.exit_count}, inside={self.is_inside})"
        )


class ActivityReporter:
    """Build per-object, per-fence summaries from an ObjectHistory."""

    def __init__(self, history: ObjectHistory) -> None:
        self._history = history

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def summarise(self, object_id: str) -> List[FenceSummary]:
        """Return a list of FenceSummary objects for every fence seen by *object_id*."""
        summaries: Dict[str, FenceSummary] = {}

        for event in self._history.events_for(object_id):
            key = event.fence_name
            if key not in summaries:
                summaries[key] = FenceSummary(object_id=object_id, fence_name=key)
            summary = summaries[key]
            if event.event_type == EventType.ENTER:
                summary.enter_count += 1
            elif event.event_type == EventType.EXIT:
                summary.exit_count += 1
            summary.last_event = event

        return list(summaries.values())

    def all_summaries(self) -> Dict[str, List[FenceSummary]]:
        """Return summaries for every tracked object."""
        return {oid: self.summarise(oid) for oid in self._history.object_ids()}

    def objects_inside(self, fence_name: str) -> List[str]:
        """Return object IDs currently believed to be inside *fence_name*."""
        result = []
        for oid, summaries in self.all_summaries().items():
            for s in summaries:
                if s.fence_name == fence_name and s.is_inside:
                    result.append(oid)
        return result
