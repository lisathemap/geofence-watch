"""Per-fence statistics tracker: entry/exit counts and average dwell time."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from geofence_watch.event import EventType, GeofenceEvent


@dataclass
class FenceStats:
    """Accumulated statistics for a single fence."""

    fence_name: str
    enter_count: int = 0
    exit_count: int = 0
    _total_dwell_seconds: float = field(default=0.0, repr=False)
    _pending_enter: Dict[str, float] = field(default_factory=dict, repr=False)

    @property
    def total_dwell_seconds(self) -> float:
        """Total accumulated dwell time across all completed visits."""
        return self._total_dwell_seconds

    @property
    def average_dwell_seconds(self) -> Optional[float]:
        """Average dwell time per completed visit, or None if no exits recorded."""
        if self.exit_count == 0:
            return None
        return self._total_dwell_seconds / self.exit_count

    def __repr__(self) -> str:  # pragma: no cover
        avg = self.average_dwell_seconds
        avg_str = f"{avg:.2f}s" if avg is not None else "n/a"
        return (
            f"FenceStats(fence={self.fence_name!r}, "
            f"enters={self.enter_count}, exits={self.exit_count}, "
            f"avg_dwell={avg_str})"
        )


class FenceStatsTracker:
    """Ingests GeofenceEvents and maintains per-fence statistics."""

    def __init__(self) -> None:
        self._stats: Dict[str, FenceStats] = {}

    def _get_or_create(self, fence_name: str) -> FenceStats:
        if fence_name not in self._stats:
            self._stats[fence_name] = FenceStats(fence_name=fence_name)
        return self._stats[fence_name]

    def ingest(self, event: GeofenceEvent) -> None:
        """Process a single event, updating the relevant fence's statistics."""
        stats = self._get_or_create(event.fence_name)
        key = (event.object_id, event.fence_name)

        if event.event_type is EventType.ENTER:
            stats.enter_count += 1
            stats._pending_enter[event.object_id] = event.timestamp

        elif event.event_type is EventType.EXIT:
            stats.exit_count += 1
            enter_ts = stats._pending_enter.pop(event.object_id, None)
            if enter_ts is not None:
                dwell = event.timestamp - enter_ts
                if dwell > 0:
                    stats._total_dwell_seconds += dwell

    def stats_for(self, fence_name: str) -> Optional[FenceStats]:
        """Return statistics for *fence_name*, or None if never seen."""
        return self._stats.get(fence_name)

    @property
    def fence_names(self) -> tuple:
        """Sorted tuple of fence names that have been observed."""
        return tuple(sorted(self._stats))

    def reset(self, fence_name: Optional[str] = None) -> None:
        """Reset stats for one fence or all fences when *fence_name* is None."""
        if fence_name is None:
            self._stats.clear()
        else:
            self._stats.pop(fence_name, None)
