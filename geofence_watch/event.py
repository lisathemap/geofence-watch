"""Event models for geofence boundary crossing notifications."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .point import Point


class EventType(Enum):
    """Type of geofence boundary event."""
    ENTER = "enter"
    EXIT = "exit"
    INSIDE = "inside"
    OUTSIDE = "outside"


@dataclass
class GeofenceEvent:
    """Represents a geofence boundary crossing or state event."""

    fence_name: str
    event_type: EventType
    point: Point
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[dict] = None

    def __repr__(self) -> str:
        return (
            f"GeofenceEvent(fence={self.fence_name!r}, "
            f"type={self.event_type.value!r}, "
            f"point={self.point}, "
            f"ts={self.timestamp.isoformat()})"
        )

    def is_transition(self) -> bool:
        """Return True if this event represents a boundary crossing."""
        return self.event_type in (EventType.ENTER, EventType.EXIT)
