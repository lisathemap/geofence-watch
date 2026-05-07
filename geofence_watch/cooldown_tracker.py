"""Tracks per-object, per-fence cooldown periods after geofence events."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

from geofence_watch.event import GeofenceEvent

# (object_id, fence_name) -> last_event_timestamp
_CooldownKey = Tuple[str, str]


@dataclass
class CooldownTracker:
    """Suppresses repeated events for the same object/fence pair within a cooldown window.

    Parameters
    ----------
    cooldown_seconds:
        Minimum number of seconds that must elapse before the same
        (object_id, fence_name) pair is allowed through again.
    clock:
        Optional callable returning the current time as a float
        (defaults to :func:`time.monotonic`).  Useful for testing.
    """

    cooldown_seconds: float
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)

    def __post_init__(self) -> None:
        if self.cooldown_seconds <= 0:
            raise ValueError(
                f"cooldown_seconds must be positive, got {self.cooldown_seconds}"
            )
        self._timestamps: Dict[_CooldownKey, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_allowed(self, event: GeofenceEvent) -> bool:
        """Return *True* if *event* is outside the cooldown window."""
        key = (event.object_id, event.fence_name)
        last = self._timestamps.get(key)
        if last is None:
            return True
        return (self.clock() - last) >= self.cooldown_seconds

    def record(self, event: GeofenceEvent) -> None:
        """Record *event* as having been forwarded (resets the cooldown)."""
        key = (event.object_id, event.fence_name)
        self._timestamps[key] = self.clock()

    def remaining(self, event: GeofenceEvent) -> float:
        """Return seconds remaining in the cooldown for *event* (0.0 if none)."""
        key = (event.object_id, event.fence_name)
        last = self._timestamps.get(key)
        if last is None:
            return 0.0
        elapsed = self.clock() - last
        return max(0.0, self.cooldown_seconds - elapsed)

    def reset(self, object_id: Optional[str] = None, fence_name: Optional[str] = None) -> None:
        """Clear cooldown state.  Pass both arguments to clear a single key;
        pass only *object_id* to clear all fences for that object;
        pass neither to clear everything."""
        if object_id is not None and fence_name is not None:
            self._timestamps.pop((object_id, fence_name), None)
        elif object_id is not None:
            keys = [k for k in self._timestamps if k[0] == object_id]
            for k in keys:
                del self._timestamps[k]
        else:
            self._timestamps.clear()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"CooldownTracker(cooldown_seconds={self.cooldown_seconds}, "
            f"tracked_keys={len(self._timestamps)})"
        )
