"""Tests for EventThrottle and ThrottleStream."""

from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.throttle import EventThrottle


def _make_event(
    object_id: str = "obj1",
    fence_name: str = "zone_a",
    event_type: EventType = EventType.ENTER,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(lon=1.0, lat=2.0),
    )


# ---------------------------------------------------------------------------
# EventThrottle construction
# ---------------------------------------------------------------------------

class TestEventThrottleInit:
    def test_default_cooldown(self):
        t = EventThrottle()
        assert t.cooldown_seconds == 30.0

    def test_custom_cooldown(self):
        t = EventThrottle(cooldown_seconds=5.0)
        assert t.cooldown_seconds == 5.0

    def test_zero_cooldown_raises(self):
        with pytest.raises(ValueError):
            EventThrottle(cooldown_seconds=0)

    def test_negative_cooldown_raises(self):
        with pytest.raises(ValueError):
            EventThrottle(cooldown_seconds=-1.0)


# ---------------------------------------------------------------------------
# EventThrottle.allow
# ---------------------------------------------------------------------------

class TestEventThrottleAllow:
    def test_first_event_always_allowed(self):
        t = EventThrottle(cooldown_seconds=10.0)
        evt = _make_event()
        assert t.allow(evt, _now=0.0) is True

    def test_second_event_within_cooldown_blocked(self):
        t = EventThrottle(cooldown_seconds=10.0)
        evt = _make_event()
        t.allow(evt, _now=0.0)
        assert t.allow(evt, _now=5.0) is False

    def test_event_after_cooldown_allowed(self):
        t = EventThrottle(cooldown_seconds=10.0)
        evt = _make_event()
        t.allow(evt, _now=0.0)
        assert t.allow(evt, _now=10.0) is True

    def test_different_fence_independent(self):
        t = EventThrottle(cooldown_seconds=10.0)
        e1 = _make_event(fence_name="zone_a")
        e2 = _make_event(fence_name="zone_b")
        t.allow(e1, _now=0.0)
        # zone_b has not been seen yet — should be allowed
        assert t.allow(e2, _now=1.0) is True

    def test_different_event_type_independent(self):
        t = EventThrottle(cooldown_seconds=10.0)
        enter = _make_event(event_type=EventType.ENTER)
        exit_ = _make_event(event_type=EventType.EXIT)
        t.allow(enter, _now=0.0)
        assert t.allow(exit_, _now=1.0) is True

    def test_reset_clears_specific_key(self):
        t = EventThrottle(cooldown_seconds=60.0)
        evt = _make_event()
        t.allow(evt, _now=0.0)
        t.reset(evt.object_id, evt.fence_name, evt.event_type)
        assert t.allow(evt, _now=1.0) is True

    def test_reset_all_clears_state(self):
        t = EventThrottle(cooldown_seconds=60.0)
        evt = _make_event()
        t.allow(evt, _now=0.0)
        t.reset_all()
        assert t.allow(evt, _now=1.0) is True

    def test_exactly_at_cooldown_boundary_allowed(self):
        """Event at exactly cooldown seconds is allowed (>=)."""
        t = EventThrottle(cooldown_seconds=10.0)
        evt = _make_event()
        t.allow(evt, _now=0.0)
        assert t.allow(evt, _now=10.0) is True
