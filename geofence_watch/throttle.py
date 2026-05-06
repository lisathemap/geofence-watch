"""Event throttling: suppress repeated events for the same object/fence within a cooldown window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from .event import EventType, GeofenceEvent


@dataclass
class ThrottleKey:
    """Composite key used to track last-seen time per (object_id, fence_name, event_type)."""

    object_id: str
    fence_name: str
    event_type: EventType

    def as_tuple(self) -> Tuple[str, str, EventType]:
        return (self.object_id, self.fence_name, self.event_type)


class EventThrottle:
    """Suppress duplicate events that occur within *cooldown_seconds* of each other.

    Parameters
    ----------
    cooldown_seconds:
        Minimum number of seconds that must elapse before the same
        (object_id, fence_name, event_type) combination is forwarded again.
    """

    def __init__(self, cooldown_seconds: float = 30.0) -> None:
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be positive")
        self._cooldown = cooldown_seconds
        self._last_seen: Dict[Tuple[str, str, EventType], float] = {}

    @property
    def cooldown_seconds(self) -> float:
        return self._cooldown

    def allow(self, event: GeofenceEvent, *, _now: Optional[float] = None) -> bool:
        """Return True if *event* should be forwarded; False if it is throttled."""
        now = _now if _now is not None else time.monotonic()
        key = (event.object_id, event.fence_name, event.event_type)
        last = self._last_seen.get(key)
        if last is None or (now - last) >= self._cooldown:
            self._last_seen[key] = now
            return True
        return False

    def reset(self, object_id: str, fence_name: str, event_type: EventType) -> None:
        """Manually clear the throttle record for a specific key."""
        key = (object_id, fence_name, event_type)
        self._last_seen.pop(key, None)

    def reset_all(self) -> None:
        """Clear all throttle state."""
        self._last_seen.clear()

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventThrottle(cooldown_seconds={self._cooldown!r}, tracked={len(self._last_seen)})"
