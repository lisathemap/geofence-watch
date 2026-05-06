"""Event deduplication: suppress consecutive identical events for the same object/fence pair."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .event import EventType, GeofenceEvent

# Key: (object_id, fence_name) -> last EventType seen
_StateKey = Tuple[str, str]


@dataclass
class EventDeduplicator:
    """Suppress consecutive duplicate events for the same (object_id, fence_name) pair.

    An event is considered a duplicate when its ``event_type`` matches the
    most-recently forwarded event for the same key.  The first event for any
    key is always forwarded.
    """

    _last_seen: Dict[_StateKey, EventType] = field(default_factory=dict, init=False, repr=False)
    _callbacks: List[Callable[[GeofenceEvent], None]] = field(
        default_factory=list, init=False, repr=False
    )

    def add_callback(self, cb: Callable[[GeofenceEvent], None]) -> None:
        """Register *cb* to receive deduplicated events."""
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[GeofenceEvent], None]) -> None:
        """Unregister *cb*. Silently ignores unknown callbacks."""
        try:
            self._callbacks.remove(cb)
        except ValueError:
            pass

    def feed(self, event: GeofenceEvent) -> bool:
        """Feed *event* into the deduplicator.

        Returns ``True`` if the event was forwarded to callbacks (i.e. it was
        not a duplicate), ``False`` otherwise.
        """
        key: _StateKey = (event.object_id, event.fence_name)
        last: Optional[EventType] = self._last_seen.get(key)

        if last is not None and last == event.event_type:
            return False

        self._last_seen[key] = event.event_type
        for cb in list(self._callbacks):
            cb(event)
        return True

    def reset(self, object_id: Optional[str] = None, fence_name: Optional[str] = None) -> None:
        """Clear stored state.

        * No arguments – clear all state.
        * ``object_id`` only – clear all entries for that object.
        * Both arguments – clear the specific (object_id, fence_name) entry.
        """
        if object_id is None:
            self._last_seen.clear()
            return
        keys_to_remove = [
            k for k in self._last_seen
            if k[0] == object_id and (fence_name is None or k[1] == fence_name)
        ]
        for k in keys_to_remove:
            del self._last_seen[k]

    @property
    def tracked_keys(self) -> List[_StateKey]:
        """Return a list of (object_id, fence_name) pairs currently tracked."""
        return list(self._last_seen.keys())

    def __repr__(self) -> str:  # pragma: no cover
        return f"EventDeduplicator(tracked_keys={len(self._last_seen)})"
