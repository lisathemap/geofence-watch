"""Tests for GeofenceStream event emission."""

import pytest
from unittest.mock import MagicMock

from geofence_watch.checker import GeofenceChecker
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.fence import Geofence
from geofence_watch.point import Point
from geofence_watch.stream import GeofenceStream


SQUARE_GEOJSON = {
    "type": "Feature",
    "properties": {"name": "test-square"},
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]
        ]],
    },
}


@pytest.fixture
def checker():
    c = GeofenceChecker()
    fence = Geofence.from_geojson(SQUARE_GEOJSON)
    c.register(fence)
    return c


@pytest.fixture
def stream(checker):
    return GeofenceStream(checker)


def test_enter_event_emitted(stream):
    outside = Point(lon=-1.0, lat=-1.0)
    inside = Point(lon=0.5, lat=0.5)
    stream.process(outside)
    events = stream.process(inside)
    assert len(events) == 1
    assert events[0].event_type == EventType.ENTER
    assert events[0].fence_name == "test-square"


def test_exit_event_emitted(stream):
    inside = Point(lon=0.5, lat=0.5)
    outside = Point(lon=2.0, lat=2.0)
    stream.process(inside)
    events = stream.process(outside)
    assert len(events) == 1
    assert events[0].event_type == EventType.EXIT


def test_no_event_when_state_unchanged(stream):
    p1 = Point(lon=0.5, lat=0.5)
    p2 = Point(lon=0.6, lat=0.6)
    stream.process(p1)
    events = stream.process(p2)
    assert events == []


def test_steady_state_emitted_when_enabled(checker):
    s = GeofenceStream(checker, emit_steady_state=True)
    inside = Point(lon=0.5, lat=0.5)
    events = s.process(inside)
    assert len(events) == 1
    assert events[0].event_type == EventType.INSIDE


def test_callback_is_called(checker):
    cb = MagicMock()
    s = GeofenceStream(checker, on_event=cb)
    stream_points = [Point(lon=-1.0, lat=-1.0), Point(lon=0.5, lat=0.5)]
    s.process_many(iter(stream_points))
    cb.assert_called_once()
    event = cb.call_args[0][0]
    assert isinstance(event, GeofenceEvent)
    assert event.event_type == EventType.ENTER


def test_reset_clears_state(stream):
    stream.process(Point(lon=0.5, lat=0.5))
    stream.reset_state()
    # After reset, first observation should not produce transition events
    events = stream.process(Point(lon=0.5, lat=0.5))
    assert all(e.event_type not in (EventType.ENTER, EventType.EXIT) for e in events)


def test_is_transition_flag():
    p = Point(lon=0.5, lat=0.5)
    enter = GeofenceEvent("z", EventType.ENTER, p)
    outside = GeofenceEvent("z", EventType.OUTSIDE, p)
    assert enter.is_transition() is True
    assert outside.is_transition() is False
