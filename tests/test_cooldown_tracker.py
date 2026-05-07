"""Tests for geofence_watch.cooldown_tracker."""

from __future__ import annotations

import pytest

from geofence_watch.cooldown_tracker import CooldownTracker
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    object_id: str = "obj1",
    fence_name: str = "zone-a",
    event_type: EventType = EventType.ENTER,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(lon=0.0, lat=0.0),
        timestamp=0.0,
    )


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestCooldownTrackerInit:
    def test_positive_cooldown_accepted(self):
        ct = CooldownTracker(cooldown_seconds=30.0)
        assert ct.cooldown_seconds == 30.0

    def test_zero_cooldown_raises(self):
        with pytest.raises(ValueError, match="positive"):
            CooldownTracker(cooldown_seconds=0.0)

    def test_negative_cooldown_raises(self):
        with pytest.raises(ValueError, match="positive"):
            CooldownTracker(cooldown_seconds=-5.0)


# ---------------------------------------------------------------------------
# is_allowed / record
# ---------------------------------------------------------------------------

class TestIsAllowed:
    def test_first_event_always_allowed(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        assert ct.is_allowed(_make_event()) is True

    def test_event_blocked_within_cooldown(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        evt = _make_event()
        ct.record(evt)
        clock.advance(5.0)
        assert ct.is_allowed(evt) is False

    def test_event_allowed_after_cooldown_expires(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        evt = _make_event()
        ct.record(evt)
        clock.advance(10.0)
        assert ct.is_allowed(evt) is True

    def test_different_object_not_affected(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        ct.record(_make_event(object_id="obj1"))
        clock.advance(1.0)
        assert ct.is_allowed(_make_event(object_id="obj2")) is True

    def test_different_fence_not_affected(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        ct.record(_make_event(fence_name="zone-a"))
        clock.advance(1.0)
        assert ct.is_allowed(_make_event(fence_name="zone-b")) is True


# ---------------------------------------------------------------------------
# remaining
# ---------------------------------------------------------------------------

class TestRemaining:
    def test_remaining_zero_when_no_record(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        assert ct.remaining(_make_event()) == 0.0

    def test_remaining_decreases_over_time(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        evt = _make_event()
        ct.record(evt)
        clock.advance(3.0)
        assert ct.remaining(evt) == pytest.approx(7.0)

    def test_remaining_zero_after_cooldown(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        evt = _make_event()
        ct.record(evt)
        clock.advance(15.0)
        assert ct.remaining(evt) == 0.0


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_specific_key(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        evt = _make_event()
        ct.record(evt)
        ct.reset(object_id="obj1", fence_name="zone-a")
        assert ct.is_allowed(evt) is True

    def test_reset_by_object_id_clears_all_fences(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        ct.record(_make_event(fence_name="zone-a"))
        ct.record(_make_event(fence_name="zone-b"))
        ct.reset(object_id="obj1")
        assert ct.is_allowed(_make_event(fence_name="zone-a")) is True
        assert ct.is_allowed(_make_event(fence_name="zone-b")) is True

    def test_reset_all_clears_everything(self):
        clock = _FakeClock()
        ct = CooldownTracker(cooldown_seconds=10.0, clock=clock)
        ct.record(_make_event(object_id="obj1", fence_name="zone-a"))
        ct.record(_make_event(object_id="obj2", fence_name="zone-b"))
        ct.reset()
        assert ct.is_allowed(_make_event(object_id="obj1", fence_name="zone-a")) is True
        assert ct.is_allowed(_make_event(object_id="obj2", fence_name="zone-b")) is True
