"""Route GeofenceEvents to named channels based on fence name or event type."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Optional

from geofence_watch.event import EventType, GeofenceEvent

_Handler = Callable[[GeofenceEvent], None]


class LabelRouter:
    """Forward events to handlers registered under a label.

    Labels can be fence names, event-type strings (``"ENTER"`` / ``"EXIT"``),
    or the special wildcard ``"*"`` which receives every event.
    """

    def __init__(self) -> None:
        self._routes: Dict[str, List[_Handler]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def subscribe(self, label: str, handler: _Handler) -> None:
        """Register *handler* under *label*."""
        if not callable(handler):
            raise TypeError(f"handler must be callable, got {type(handler).__name__}")
        if not isinstance(label, str) or not label:
            raise ValueError("label must be a non-empty string")
        self._routes[label].append(handler)

    def unsubscribe(self, label: str, handler: _Handler) -> None:
        """Remove *handler* from *label*.  Silent if not registered."""
        if label in self._routes:
            try:
                self._routes[label].remove(handler)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(self, event: GeofenceEvent) -> None:
        """Dispatch *event* to all matching handlers."""
        labels = {
            event.fence_name,
            event.event_type.name,
            "*",
        }
        seen: set = set()
        for label in labels:
            for handler in list(self._routes.get(label, [])):
                if id(handler) not in seen:
                    seen.add(id(handler))
                    handler(event)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def labels(self) -> List[str]:
        """Sorted list of labels that have at least one subscriber."""
        return sorted(k for k, v in self._routes.items() if v)

    def subscriber_count(self, label: str) -> int:
        """Return number of handlers registered under *label*."""
        return len(self._routes.get(label, []))

    def __repr__(self) -> str:  # pragma: no cover
        return f"LabelRouter(labels={self.labels})"
