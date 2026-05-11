"""Tests for geofence_watch.idle_detector."""
from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.idle_detector import IdleDetector, IdleRecord
from geofence_watch.point import Point


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeClock:
    def __init__(self, start: float = 1_000.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_event(
    object_id: str = "obj1",
    fence_name: str = "zone_a",
    etype: EventType = EventType.ENTER,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=etype,
        point=Point(lon=0.0, lat=0.0),
        timestamp=1_000.0,
    )


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestIdleDetectorInit:
    def test_default_threshold(self):
        d = IdleDetector()
        assert d.threshold_seconds == 60.0

    def test_custom_threshold(self):
        d = IdleDetector(threshold_seconds=30.0)
        assert d.threshold_seconds == 30.0

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError):
            IdleDetector(threshold_seconds=0)

    def test_negative_threshold_raises(self):
        with pytest.raises(ValueError):
            IdleDetector(threshold_seconds=-5)

    def test_no_tracked_objects_initially(self):
        d = IdleDetector()
        assert d.tracked_objects == []


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

class TestIngest:
    def test_ingest_adds_object(self):
        clock = _FakeClock()
        d = IdleDetector(threshold_seconds=10.0, clock=clock)
        d.ingest(_make_event("obj1"))
        assert "obj1" in d.tracked_objects

    def test_ingest_multiple_objects(self):
        clock = _FakeClock()
        d = IdleDetector(threshold_seconds=10.0, clock=clock)
        d.ingest(_make_event("obj1"))
        d.ingest(_make_event("obj2"))
        assert set(d.tracked_objects) == {"obj1", "obj2"}

    def test_ingest_updates_timestamp(self):
        clock = _FakeClock()
        d = IdleDetector(threshold_seconds=10.0, clock=clock)
        d.ingest(_make_event("obj1"))
        clock.advance(5)
        d.ingest(_make_event("obj1"))  # refresh
        clock.advance(8)              # only 8 s since refresh
        assert d.idle_objects() == []


# ---------------------------------------------------------------------------
# idle_objects
# ---------------------------------------------------------------------------

class TestIdleObjects:
    def test_not_idle_before_threshold(self):
        clock = _FakeClock()
        d = IdleDetector(threshold_seconds=10.0, clock=clock)
        d.ingest(_make_event("obj1"))
        clock.advance(9)
        assert d.idle_objects() == []

    def test_idle_at_threshold(self):
        clock = _FakeClock()
        d = IdleDetector(threshold_seconds=10.0, clock=clock)
        d.ingest(_make_event("obj1"))
        clock.advance(10)
        records = d.idle_objects()
        assert len(records) == 1
        assert records[0].object_id == "obj1"

    def test_idle_record_fence_name(self):
        clock = _FakeClock()
        d = IdleDetector(threshold_seconds=5.0, clock=clock)
        d.ingest(_make_event("obj1", fence_name="zone_b"))
        clock.advance(6)
        records = d.idle_objects()
        assert records[0].last_fence == "zone_b"

    def test_idle_seconds_approximate(self):
        clock = _FakeClock()
        d = IdleDetector(threshold_seconds=5.0, clock=clock)
        d.ingest(_make_event("obj1"))
        clock.advance(15)
        records = d.idle_objects()
        assert abs(records[0].idle_seconds - 15.0) < 0.01

    def test_multiple_objects_only_idle_returned(self):
        clock = _FakeClock()
        d = IdleDetector(threshold_seconds=10.0, clock=clock)
        d.ingest(_make_event("obj1"))
        clock.advance(5)
        d.ingest(_make_event("obj2"))  # ingested later
        clock.advance(6)              # obj1 = 11 s idle, obj2 = 6 s
        records = d.idle_objects()
        assert len(records) == 1
        assert records[0].object_id == "obj1"


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

class TestCallbacks:
    def test_add_callback(self):
        d = IdleDetector()
        cb = lambda recs: None
        d.add_callback(cb)
        assert cb.__name__ in d.callback_names or repr(cb) in d.callback_names

    def test_non_callable_raises(self):
        d = IdleDetector()
        with pytest.raises(TypeError):
            d.add_callback("not_callable")  # type: ignore

    def test_duplicate_callback_not_added_twice(self):
        d = IdleDetector()
        cb = lambda recs: None
        d.add_callback(cb)
        d.add_callback(cb)
        assert len(d._callbacks) == 1

    def test_remove_callback(self):
        d = IdleDetector()
        cb = lambda recs: None
        d.add_callback(cb)
        d.remove_callback(cb)
        assert len(d._callbacks) == 0

    def test_check_and_notify_fires_callback(self):
        clock = _FakeClock()
        d = IdleDetector(threshold_seconds=5.0, clock=clock)
        d.ingest(_make_event("obj1"))
        clock.advance(6)
        received: list = []
        d.add_callback(received.extend)
        d.check_and_notify()
        assert len(received) == 1
        assert received[0].object_id == "obj1"

    def test_check_and_notify_no_callback_when_no_idle(self):
        clock = _FakeClock()
        d = IdleDetector(threshold_seconds=10.0, clock=clock)
        d.ingest(_make_event("obj1"))
        clock.advance(3)
        fired = []
        d.add_callback(lambda recs: fired.extend(recs))
        d.check_and_notify()
        assert fired == []
