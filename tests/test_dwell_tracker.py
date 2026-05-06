"""Tests for DwellTracker."""
from __future__ import annotations

import pytest

from geofence_watch.dwell_tracker import DwellRecord, DwellTracker
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(event_type: EventType, object_id: str = "obj1", fence: str = "zone_a") -> GeofenceEvent:
    return GeofenceEvent(
        event_type=event_type,
        object_id=object_id,
        fence_name=fence,
        point=Point(lon=0.0, lat=0.0),
        timestamp=0.0,
    )


class _FakeClock:
    """Controllable monotonic clock for deterministic tests."""

    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


# ---------------------------------------------------------------------------
# DwellRecord
# ---------------------------------------------------------------------------

class TestDwellRecord:
    def test_elapsed_uses_clock(self):
        clock = _FakeClock(100.0)
        rec = DwellRecord(object_id="a", fence_name="f", entered_at=100.0, _clock=clock)
        clock.advance(5.0)
        assert rec.elapsed() == pytest.approx(5.0)

    def test_elapsed_zero_at_entry(self):
        clock = _FakeClock(50.0)
        rec = DwellRecord(object_id="a", fence_name="f", entered_at=50.0, _clock=clock)
        assert rec.elapsed() == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# DwellTracker — basic ingestion
# ---------------------------------------------------------------------------

class TestDwellTrackerIngest:
    def test_enter_returns_none(self):
        tracker = DwellTracker()
        result = tracker.ingest(_make_event(EventType.ENTER))
        assert result is None

    def test_exit_returns_dwell_seconds(self):
        clock = _FakeClock(0.0)
        tracker = DwellTracker(clock=clock)
        tracker.ingest(_make_event(EventType.ENTER))
        clock.advance(10.0)
        result = tracker.ingest(_make_event(EventType.EXIT))
        assert result == pytest.approx(10.0)

    def test_exit_without_enter_returns_none(self):
        tracker = DwellTracker()
        result = tracker.ingest(_make_event(EventType.EXIT))
        assert result is None

    def test_last_dwell_stored_after_exit(self):
        clock = _FakeClock(0.0)
        tracker = DwellTracker(clock=clock)
        tracker.ingest(_make_event(EventType.ENTER))
        clock.advance(7.5)
        tracker.ingest(_make_event(EventType.EXIT))
        assert tracker.last_dwell("obj1", "zone_a") == pytest.approx(7.5)

    def test_last_dwell_none_before_any_exit(self):
        tracker = DwellTracker()
        assert tracker.last_dwell("obj1", "zone_a") is None


# ---------------------------------------------------------------------------
# current_dwell
# ---------------------------------------------------------------------------

class TestCurrentDwell:
    def test_current_dwell_while_inside(self):
        clock = _FakeClock(0.0)
        tracker = DwellTracker(clock=clock)
        tracker.ingest(_make_event(EventType.ENTER))
        clock.advance(3.0)
        assert tracker.current_dwell("obj1", "zone_a") == pytest.approx(3.0)

    def test_current_dwell_none_when_not_inside(self):
        tracker = DwellTracker()
        assert tracker.current_dwell("obj1", "zone_a") is None

    def test_current_dwell_cleared_after_exit(self):
        clock = _FakeClock(0.0)
        tracker = DwellTracker(clock=clock)
        tracker.ingest(_make_event(EventType.ENTER))
        tracker.ingest(_make_event(EventType.EXIT))
        assert tracker.current_dwell("obj1", "zone_a") is None


# ---------------------------------------------------------------------------
# active_objects & reset
# ---------------------------------------------------------------------------

class TestActiveObjectsAndReset:
    def test_active_objects_empty_initially(self):
        tracker = DwellTracker()
        assert tracker.active_objects() == {}

    def test_active_objects_contains_entered(self):
        clock = _FakeClock(0.0)
        tracker = DwellTracker(clock=clock)
        tracker.ingest(_make_event(EventType.ENTER, object_id="a", fence="z1"))
        tracker.ingest(_make_event(EventType.ENTER, object_id="b", fence="z2"))
        clock.advance(2.0)
        active = tracker.active_objects()
        assert ("a", "z1") in active
        assert ("b", "z2") in active
        assert active[("a", "z1")] == pytest.approx(2.0)

    def test_reset_clears_all_state(self):
        clock = _FakeClock(0.0)
        tracker = DwellTracker(clock=clock)
        tracker.ingest(_make_event(EventType.ENTER))
        clock.advance(1.0)
        tracker.ingest(_make_event(EventType.EXIT))
        tracker.reset()
        assert tracker.active_objects() == {}
        assert tracker.last_dwell("obj1", "zone_a") is None
