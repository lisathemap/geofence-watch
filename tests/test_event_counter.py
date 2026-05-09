"""Tests for geofence_watch.event_counter."""
from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.event_counter import EventCounter
from geofence_watch.point import Point


def _make_event(
    object_id: str = "obj1",
    fence_name: str = "zone_a",
    event_type: EventType = EventType.ENTER,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(lon=0.0, lat=0.0),
    )


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestEventCounterInit:
    def test_default_track_types_is_none(self):
        ec = EventCounter()
        assert ec._track_types is None

    def test_custom_track_types_stored_as_tuple(self):
        ec = EventCounter(track_types=(EventType.ENTER,))
        assert ec._track_types == (EventType.ENTER,)

    def test_total_starts_at_zero(self):
        assert EventCounter().total == 0


# ---------------------------------------------------------------------------
# ingest
# ---------------------------------------------------------------------------

class TestIngest:
    def test_non_event_raises(self):
        ec = EventCounter()
        with pytest.raises(TypeError):
            ec.ingest("not-an-event")  # type: ignore[arg-type]

    def test_enter_increments_count(self):
        ec = EventCounter()
        ec.ingest(_make_event(event_type=EventType.ENTER))
        assert ec.count("obj1", "zone_a", EventType.ENTER) == 1

    def test_multiple_ingests_accumulate(self):
        ec = EventCounter()
        for _ in range(5):
            ec.ingest(_make_event())
        assert ec.count("obj1", "zone_a", EventType.ENTER) == 5

    def test_filtered_type_not_counted(self):
        ec = EventCounter(track_types=(EventType.ENTER,))
        ec.ingest(_make_event(event_type=EventType.EXIT))
        assert ec.total == 0

    def test_allowed_type_is_counted_when_filter_active(self):
        ec = EventCounter(track_types=(EventType.ENTER,))
        ec.ingest(_make_event(event_type=EventType.ENTER))
        assert ec.total == 1

    def test_different_objects_tracked_separately(self):
        ec = EventCounter()
        ec.ingest(_make_event(object_id="a"))
        ec.ingest(_make_event(object_id="b"))
        assert ec.count("a", "zone_a", EventType.ENTER) == 1
        assert ec.count("b", "zone_a", EventType.ENTER) == 1


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

class TestAggregation:
    def test_total_for_object(self):
        ec = EventCounter()
        ec.ingest(_make_event(object_id="x", fence_name="f1"))
        ec.ingest(_make_event(object_id="x", fence_name="f2"))
        ec.ingest(_make_event(object_id="y", fence_name="f1"))
        assert ec.total_for_object("x") == 2

    def test_total_for_fence(self):
        ec = EventCounter()
        ec.ingest(_make_event(object_id="a", fence_name="home"))
        ec.ingest(_make_event(object_id="b", fence_name="home"))
        ec.ingest(_make_event(object_id="a", fence_name="work"))
        assert ec.total_for_fence("home") == 2

    def test_grand_total(self):
        ec = EventCounter()
        for _ in range(3):
            ec.ingest(_make_event())
        assert ec.total == 3

    def test_unknown_key_returns_zero(self):
        ec = EventCounter()
        assert ec.count("nobody", "nowhere", EventType.ENTER) == 0


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_full_reset_clears_all(self):
        ec = EventCounter()
        ec.ingest(_make_event(object_id="a"))
        ec.ingest(_make_event(object_id="b"))
        ec.reset()
        assert ec.total == 0

    def test_partial_reset_clears_only_target(self):
        ec = EventCounter()
        ec.ingest(_make_event(object_id="a"))
        ec.ingest(_make_event(object_id="b"))
        ec.reset(object_id="a")
        assert ec.total_for_object("a") == 0
        assert ec.total_for_object("b") == 1

    def test_reset_unknown_object_is_noop(self):
        ec = EventCounter()
        ec.ingest(_make_event())
        ec.reset(object_id="ghost")
        assert ec.total == 1
