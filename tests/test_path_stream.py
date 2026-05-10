"""Tests for PathStream."""
from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.path_tracker import PathTracker
from geofence_watch.path_stream import PathStream


def _make_event(
    oid: str = "obj1",
    fence: str = "fence_a",
    etype: EventType = EventType.ENTER,
    ts: float = 0.0,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=oid,
        fence_name=fence,
        event_type=etype,
        timestamp=ts,
        lat=0.0,
        lon=0.0,
    )


@pytest.fixture
def stream():
    return PathStream()


class TestPathStreamInit:
    def test_default_tracker_created(self, stream):
        assert isinstance(stream.tracker, PathTracker)

    def test_custom_tracker_accepted(self):
        t = PathTracker(max_path_length=3)
        s = PathStream(tracker=t)
        assert s.tracker is t

    def test_invalid_tracker_raises(self):
        with pytest.raises(TypeError):
            PathStream(tracker="not_a_tracker")

    def test_no_callbacks_initially(self, stream):
        assert stream.callback_names == ()


def test_process_enter_updates_path(stream):
    stream.process(_make_event("obj1", "fence_a", EventType.ENTER))
    rec = stream.path_for("obj1")
    assert rec is not None
    assert "fence_a" in rec.path


def test_process_non_event_raises(stream):
    with pytest.raises(TypeError):
        stream.process("not_an_event")


def test_add_and_remove_callback(stream):
    results = []
    stream.add_callback("cb", results.append)
    assert "cb" in stream.callback_names
    stream.remove_callback("cb")
    assert "cb" not in stream.callback_names


def test_callback_receives_path_record(stream):
    records = []
    stream.add_callback("r", records.append)
    stream.process(_make_event("obj1", "zone_x", EventType.ENTER))
    assert len(records) == 1
    assert records[0].path == ["zone_x"]


def test_path_for_unknown_is_none(stream):
    assert stream.path_for("unknown") is None


def test_max_path_length_forwarded_to_tracker():
    s = PathStream(max_path_length=2)
    assert s.tracker.max_path_length == 2


def test_track_objects_forwarded_to_tracker():
    s = PathStream(track_objects=("a",))
    assert s.tracker.tracked_objects == ("a",)
