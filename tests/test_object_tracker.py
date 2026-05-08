"""Tests for geofence_watch.object_tracker."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.object_tracker import ObjectState, ObjectTracker
from geofence_watch.point import Point

_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _make_event(
    object_id: str,
    fence_name: str,
    event_type: EventType,
    lon: float = 0.0,
    lat: float = 0.0,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(lon, lat),
        timestamp=_NOW,
    )


# ---------------------------------------------------------------------------
# ObjectState
# ---------------------------------------------------------------------------

class TestObjectState:
    def test_default_active_fences_empty(self):
        s = ObjectState(object_id="obj1")
        assert s.active_fences == frozenset()

    def test_default_last_point_none(self):
        s = ObjectState(object_id="obj1")
        assert s.last_point is None


# ---------------------------------------------------------------------------
# ObjectTracker — initialisation
# ---------------------------------------------------------------------------

class TestObjectTrackerInit:
    def test_starts_empty(self):
        t = ObjectTracker()
        assert len(t) == 0

    def test_object_ids_empty(self):
        t = ObjectTracker()
        assert t.object_ids == frozenset()


# ---------------------------------------------------------------------------
# ObjectTracker — ingest
# ---------------------------------------------------------------------------

class TestObjectTrackerIngest:
    def test_invalid_type_raises(self):
        t = ObjectTracker()
        with pytest.raises(TypeError):
            t.ingest("not-an-event")  # type: ignore[arg-type]

    def test_enter_adds_to_active_fences(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-a", EventType.ENTER))
        assert "zone-a" in t.state_for("car1").active_fences

    def test_exit_removes_from_active_fences(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-a", EventType.ENTER))
        t.ingest(_make_event("car1", "zone-a", EventType.EXIT))
        assert "zone-a" not in t.state_for("car1").active_fences

    def test_last_point_updated(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-a", EventType.ENTER, lon=10.0, lat=20.0))
        assert t.state_for("car1").last_point == Point(10.0, 20.0)

    def test_multiple_fences_tracked(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-a", EventType.ENTER))
        t.ingest(_make_event("car1", "zone-b", EventType.ENTER))
        assert t.state_for("car1").active_fences == frozenset({"zone-a", "zone-b"})

    def test_exit_non_entered_fence_is_noop(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-x", EventType.EXIT))
        assert t.state_for("car1").active_fences == frozenset()

    def test_multiple_objects_independent(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-a", EventType.ENTER))
        t.ingest(_make_event("car2", "zone-b", EventType.ENTER))
        assert "zone-a" not in t.state_for("car2").active_fences
        assert "zone-b" not in t.state_for("car1").active_fences


# ---------------------------------------------------------------------------
# ObjectTracker — query helpers
# ---------------------------------------------------------------------------

class TestObjectTrackerQuery:
    def test_is_inside_true(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-a", EventType.ENTER))
        assert t.is_inside("car1", "zone-a") is True

    def test_is_inside_false_after_exit(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-a", EventType.ENTER))
        t.ingest(_make_event("car1", "zone-a", EventType.EXIT))
        assert t.is_inside("car1", "zone-a") is False

    def test_is_inside_unknown_object(self):
        t = ObjectTracker()
        assert t.is_inside("ghost", "zone-a") is False

    def test_state_for_unknown_returns_none(self):
        t = ObjectTracker()
        assert t.state_for("nobody") is None

    def test_object_ids_populated(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-a", EventType.ENTER))
        t.ingest(_make_event("car2", "zone-b", EventType.ENTER))
        assert t.object_ids == frozenset({"car1", "car2"})


# ---------------------------------------------------------------------------
# ObjectTracker — reset
# ---------------------------------------------------------------------------

class TestObjectTrackerReset:
    def test_reset_specific_object(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-a", EventType.ENTER))
        t.reset("car1")
        assert t.state_for("car1") is None

    def test_reset_all(self):
        t = ObjectTracker()
        t.ingest(_make_event("car1", "zone-a", EventType.ENTER))
        t.ingest(_make_event("car2", "zone-b", EventType.ENTER))
        t.reset()
        assert len(t) == 0

    def test_reset_unknown_object_is_noop(self):
        t = ObjectTracker()
        t.reset("ghost")  # should not raise
        assert len(t) == 0
