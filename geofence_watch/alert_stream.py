"""AlertStream: wraps GeofenceStream and pipes events through AlertManager."""
from __future__ import annotations

from typing import List, Optional

from geofence_watch.alert import AlertManager, AlertRule
from geofence_watch.checker import GeofenceChecker
from geofence_watch.event import GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.stream import GeofenceStream


class AlertStream:
    """Combines GeofenceStream with AlertManager for event-driven alerting."""

    def __init__(
        self,
        checker: GeofenceChecker,
        alert_manager: Optional[AlertManager] = None,
    ) -> None:
        self._stream = GeofenceStream(checker)
        self._alerts = alert_manager if alert_manager is not None else AlertManager()

    # ------------------------------------------------------------------
    # Delegation helpers
    # ------------------------------------------------------------------

    def add_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._alerts.add_rule(rule)

    def remove_rule(self, name: str) -> None:
        """Unregister an alert rule by name."""
        self._alerts.remove_rule(name)

    @property
    def rule_names(self) -> List[str]:
        return self._alerts.rule_names

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self, object_id: str, point: Point) -> List[GeofenceEvent]:
        """Process a coordinate update and fire any matching alert callbacks.

        Returns the list of GeofenceEvents produced (same as GeofenceStream).
        """
        events = self._stream.process(object_id, point)
        for event in events:
            self._alerts.evaluate(event)
        return events

    def reset(self, object_id: Optional[str] = None) -> None:
        """Reset tracking state for one or all objects."""
        self._stream.reset(object_id)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"AlertStream(rules={self.rule_names}, "
            f"fences={self._stream._checker.fence_names})"
        )
