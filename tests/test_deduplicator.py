"""Tests for EventDeduplicator and DedupStream."""

import pytest
from unittest.mock import MagicMock

from geofence_watch.deduplicator import EventDeduplicator
from geofence_watch.dedup_stream import DedupStream
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point

import datetime


def _make_event(
    object_id: str = "obj-1",
    fence_name: str = "zone-a",
    event_type: EventType = EventType.ENTER,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(lon=0.0, lat=0.0),
        timestamp=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
    )


# ---------------------------------------------------------------------------
# EventDeduplicator unit tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def dedup() -> EventDeduplicator:
    return EventDeduplicator()


def test_first_event_always_forwarded(dedup):
    cb = MagicMock()
    dedup.add_callback(cb)
    evt = _make_event(event_type=EventType.ENTER)
    result = dedup.feed(evt)
    assert result is True
    cb.assert_called_once_with(evt)


def test_duplicate_event_suppressed(dedup):
    cb = MagicMock()
    dedup.add_callback(cb)
    evt = _make_event(event_type=EventType.ENTER)
    dedup.feed(evt)
    result = dedup.feed(evt)  # same type again
    assert result is False
    assert cb.call_count == 1


def test_different_type_forwarded(dedup):
    cb = MagicMock()
    dedup.add_callback(cb)
    dedup.feed(_make_event(event_type=EventType.ENTER))
    result = dedup.feed(_make_event(event_type=EventType.EXIT))
    assert result is True
    assert cb.call_count == 2


def test_different_fence_independent(dedup):
    cb = MagicMock()
    dedup.add_callback(cb)
    dedup.feed(_make_event(fence_name="zone-a", event_type=EventType.ENTER))
    # Same event type but different fence — should forward
    result = dedup.feed(_make_event(fence_name="zone-b", event_type=EventType.ENTER))
    assert result is True


def test_tracked_keys_populated(dedup):
    dedup.feed(_make_event(object_id="a", fence_name="f1"))
    dedup.feed(_make_event(object_id="b", fence_name="f1"))
    assert ("a", "f1") in dedup.tracked_keys
    assert ("b", "f1") in dedup.tracked_keys


def test_reset_all(dedup):
    dedup.feed(_make_event(object_id="a", fence_name="f1"))
    dedup.reset()
    assert dedup.tracked_keys == []


def test_reset_by_object_id(dedup):
    dedup.feed(_make_event(object_id="a", fence_name="f1"))
    dedup.feed(_make_event(object_id="b", fence_name="f1"))
    dedup.reset(object_id="a")
    assert ("a", "f1") not in dedup.tracked_keys
    assert ("b", "f1") in dedup.tracked_keys


def test_reset_specific_key(dedup):
    dedup.feed(_make_event(object_id="a", fence_name="f1"))
    dedup.feed(_make_event(object_id="a", fence_name="f2"))
    dedup.reset(object_id="a", fence_name="f1")
    assert ("a", "f1") not in dedup.tracked_keys
    assert ("a", "f2") in dedup.tracked_keys


def test_remove_callback(dedup):
    cb = MagicMock()
    dedup.add_callback(cb)
    dedup.remove_callback(cb)
    dedup.feed(_make_event())
    cb.assert_not_called()


def test_remove_unknown_callback_no_error(dedup):
    dedup.remove_callback(lambda e: None)  # should not raise


# ---------------------------------------------------------------------------
# DedupStream integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def checker():
    from geofence_watch.checker import GeofenceChecker
    from geofence_watch.fence import Geofence

    geojson = {
        "type": "Feature",
        "properties": {"name": "zone-a"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        },
    }
    c = GeofenceChecker()
    c.register(Geofence.from_geojson(geojson))
    return c


@pytest.fixture()
def ds(checker):
    from geofence_watch.stream import GeofenceStream
    return DedupStream(GeofenceStream(checker))


def test_dedup_stream_stream_property(ds):
    from geofence_watch.stream import GeofenceStream
    assert isinstance(ds.stream, GeofenceStream)


def test_dedup_stream_deduplicator_property(ds):
    assert isinstance(ds.deduplicator, EventDeduplicator)


def test_dedup_stream_suppresses_duplicate(ds):
    cb = MagicMock()
    ds.add_callback(cb)
    inside = Point(lon=0.5, lat=0.5)
    ds.process("truck-1", inside)
    ds.process("truck-1", inside)  # still inside — no new event expected
    # Only one ENTER should reach the callback
    assert cb.call_count == 1
