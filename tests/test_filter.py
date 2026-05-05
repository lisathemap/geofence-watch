"""Tests for geofence_watch.filter."""

from datetime import datetime, timezone

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.filter import EventFilter
from geofence_watch.point import Point


def _evt(
    object_id: str = "obj1",
    fence_name: str = "zone_a",
    event_type: EventType = EventType.ENTER,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(0.0, 0.0),
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


class TestEventFilterMatches:
    def test_empty_filter_passes_all(self):
        f = EventFilter()
        assert f.matches(_evt())

    def test_filter_by_event_type_pass(self):
        f = EventFilter(event_types=[EventType.ENTER])
        assert f.matches(_evt(event_type=EventType.ENTER))

    def test_filter_by_event_type_block(self):
        f = EventFilter(event_types=[EventType.EXIT])
        assert not f.matches(_evt(event_type=EventType.ENTER))

    def test_filter_by_fence_name_pass(self):
        f = EventFilter(fence_names=["zone_a"])
        assert f.matches(_evt(fence_name="zone_a"))

    def test_filter_by_fence_name_block(self):
        f = EventFilter(fence_names=["zone_b"])
        assert not f.matches(_evt(fence_name="zone_a"))

    def test_filter_by_object_id_pass(self):
        f = EventFilter(object_ids=["obj1"])
        assert f.matches(_evt(object_id="obj1"))

    def test_filter_by_object_id_block(self):
        f = EventFilter(object_ids=["obj2"])
        assert not f.matches(_evt(object_id="obj1"))

    def test_multiple_criteria_all_pass(self):
        f = EventFilter(
            event_types=[EventType.ENTER],
            fence_names=["zone_a"],
            object_ids=["obj1"],
        )
        assert f.matches(_evt())

    def test_multiple_criteria_one_fails(self):
        f = EventFilter(
            event_types=[EventType.ENTER],
            fence_names=["zone_b"],  # wrong fence
        )
        assert not f.matches(_evt())

    def test_custom_predicate_pass(self):
        f = EventFilter()
        f.add_custom(lambda e: e.object_id.startswith("obj"))
        assert f.matches(_evt(object_id="obj42"))

    def test_custom_predicate_block(self):
        f = EventFilter()
        f.add_custom(lambda e: e.object_id.startswith("vehicle"))
        assert not f.matches(_evt(object_id="obj1"))


class TestEventFilterApply:
    def _events(self):
        return [
            _evt("a", "zone_a", EventType.ENTER),
            _evt("b", "zone_b", EventType.EXIT),
            _evt("a", "zone_a", EventType.EXIT),
            _evt("c", "zone_a", EventType.ENTER),
        ]

    def test_apply_no_filter(self):
        f = EventFilter()
        assert len(f.apply(self._events())) == 4

    def test_apply_by_type(self):
        f = EventFilter(event_types=[EventType.ENTER])
        result = f.apply(self._events())
        assert len(result) == 2
        assert all(e.event_type == EventType.ENTER for e in result)

    def test_apply_by_object_and_type(self):
        f = EventFilter(object_ids=["a"], event_types=[EventType.EXIT])
        result = f.apply(self._events())
        assert len(result) == 1
        assert result[0].object_id == "a"
        assert result[0].event_type == EventType.EXIT

    def test_apply_returns_empty_when_none_match(self):
        f = EventFilter(fence_names=["zone_z"])
        assert f.apply(self._events()) == []
