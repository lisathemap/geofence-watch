"""Alert rules: trigger callbacks when geofence events match criteria."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from geofence_watch.event import EventType, GeofenceEvent


@dataclass
class AlertRule:
    """Defines a condition and callback for a geofence alert."""

    name: str
    fence_name: str
    event_type: EventType
    callback: Callable[[GeofenceEvent], None]
    object_id: Optional[str] = None  # None means match any object

    def matches(self, event: GeofenceEvent) -> bool:
        """Return True if the event satisfies this rule."""
        if event.fence_name != self.fence_name:
            return False
        if event.event_type != self.event_type:
            return False
        if self.object_id is not None and event.object_id != self.object_id:
            return False
        return True

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"AlertRule(name={self.name!r}, fence={self.fence_name!r}, "
            f"event_type={self.event_type.name}, object_id={self.object_id!r})"
        )


class AlertManager:
    """Registers alert rules and dispatches callbacks when events match."""

    def __init__(self) -> None:
        self._rules: List[AlertRule] = []

    def add_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        if any(r.name == rule.name for r in self._rules):
            raise ValueError(f"Rule with name {rule.name!r} already exists.")
        self._rules.append(rule)

    def remove_rule(self, name: str) -> None:
        """Unregister an alert rule by name."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.name != name]
        if len(self._rules) == before:
            raise KeyError(f"No rule named {name!r}")

    @property
    def rule_names(self) -> List[str]:
        return [r.name for r in self._rules]

    def evaluate(self, event: GeofenceEvent) -> int:
        """Evaluate event against all rules; fire matching callbacks.

        Returns the number of rules that fired.
        """
        fired = 0
        for rule in self._rules:
            if rule.matches(event):
                rule.callback(event)
                fired += 1
        return fired

    def __len__(self) -> int:
        return len(self._rules)

    def __repr__(self) -> str:  # pragma: no cover
        return f"AlertManager(rules={self.rule_names})"
