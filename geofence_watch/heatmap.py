"""Heatmap builder: accumulates visit counts per fence per object."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .event import EventType, GeofenceEvent


@dataclass
class HeatmapCell:
    """Visit count for a single (object_id, fence_name) pair."""

    object_id: str
    fence_name: str
    enter_count: int = 0

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"HeatmapCell(object_id={self.object_id!r}, "
            f"fence_name={self.fence_name!r}, enter_count={self.enter_count})"
        )


class HeatmapBuilder:
    """Accumulates ENTER events and exposes per-fence and per-object counts."""

    def __init__(self) -> None:
        # _counts[object_id][fence_name] = enter_count
        self._counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def ingest(self, event: GeofenceEvent) -> None:
        """Record an event; only ENTER events increment the counter."""
        if not isinstance(event, GeofenceEvent):
            raise TypeError(f"Expected GeofenceEvent, got {type(event).__name__}")
        if event.event_type is EventType.ENTER:
            self._counts[event.object_id][event.fence_name] += 1

    def count(self, object_id: str, fence_name: str) -> int:
        """Return the number of times *object_id* entered *fence_name*."""
        return self._counts.get(object_id, {}).get(fence_name, 0)

    def top_fences(self, n: int = 5) -> List[Tuple[str, int]]:
        """Return the top-n fences by total enter count across all objects."""
        if n < 1:
            raise ValueError("n must be >= 1")
        totals: Dict[str, int] = defaultdict(int)
        for obj_counts in self._counts.values():
            for fence, cnt in obj_counts.items():
                totals[fence] += cnt
        return sorted(totals.items(), key=lambda x: x[1], reverse=True)[:n]

    def cells(self, fence_name: Optional[str] = None) -> List[HeatmapCell]:
        """Return all HeatmapCell records, optionally filtered by fence."""
        result = []
        for obj_id, obj_counts in self._counts.items():
            for fn, cnt in obj_counts.items():
                if fence_name is None or fn == fence_name:
                    result.append(HeatmapCell(obj_id, fn, cnt))
        return result

    def reset(self) -> None:
        """Clear all accumulated counts."""
        self._counts.clear()

    def __repr__(self) -> str:  # pragma: no cover
        total = sum(c for obj in self._counts.values() for c in obj.values())
        return f"HeatmapBuilder(total_enters={total})"
