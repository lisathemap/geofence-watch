"""Tests for PathTracker and PathRecord."""
from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.path_tracker import PathRecord, PathTracker


def _make_event(
    oid: str,
    fence: str,
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


# ---------------------------------------------------------------------------
# PathRecord
# ---------------------------------------------------------------------------

class TestPathRecord:
    def test_empty_path(self):
        r = PathRecord(object_id="obj1")
        assert r.path == []
        assert len(r) == 0

    def test_append_grows_path(self):
        r = PathRecord(object_id="obj1")
        r.append("zone_a", 1.0)
        r.append("zone_b", 2.0)
        assert r.path == ["zone_a", "zone_b"]
        assert len(r) == 2

    def test_entries_contain_timestamps(self):
        r = PathRecord(object_id="obj1")
        r.append("zone_a", 99.5)
        assert r.entries == [("zone_a", 99.5)]


# ---------------------------------------------------------------------------
# PathTracker init
# ---------------------------------------------------------------------------

class TestPathTrackerInit:
    def test_default_max_is_none(self):
        t = PathTracker()
        assert t.max_path_length is None

    def test_custom_max_stored(self):
        t = PathTracker(max_path_length=5)
        assert t.max_path_length == 5

    def test_zero_max_raises(self):
        with pytest.raises(ValueError):
            PathTracker(max_path_length=0)

    def test_negative_max_raises(self):
        with pytest.raises(ValueError):
            PathTracker(max_path_length=-1)

    def test_track_objects_stored_as_tuple(self):
        t = PathTracker(track_objects=["a", "b"])
        assert t.tracked_objects == ("a", "b")

    def test_no_callbacks_initially(self):
        t = PathTracker()
        assert t.callback_names == ()


# ---------------------------------------------------------------------------
# PathTracker.ingest
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker():
    return PathTracker()


def test_enter_event_recorded(tracker):
    tracker.ingest(_make_event("obj1", "fence_a", EventType.ENTER, ts=1.0))
    rec = tracker.path_for("obj1")
    assert rec is not None
    assert rec.path == ["fence_a"]


def test_exit_event_ignored(tracker):
    tracker.ingest(_make_event("obj1", "fence_a", EventType.EXIT, ts=1.0))
    assert tracker.path_for("obj1") is None


def test_multiple_enters_ordered(tracker):
    for fence in ["a", "b", "c"]:
        tracker.ingest(_make_event("obj1", fence, EventType.ENTER))
    assert tracker.path_for("obj1").path == ["a", "b", "c"]


def test_max_path_length_truncates():
    t = PathTracker(max_path_length=2)
    for fence in ["a", "b", "c"]:
        t.ingest(_make_event("obj1", fence, EventType.ENTER))
    assert t.path_for("obj1").path == ["b", "c"]


def test_track_objects_filters_others():
    t = PathTracker(track_objects=("allowed",))
    t.ingest(_make_event("allowed", "fence_a", EventType.ENTER))
    t.ingest(_make_event("ignored", "fence_b", EventType.ENTER))
    assert t.path_for("allowed") is not None
    assert t.path_for("ignored") is None


def test_callback_called_on_enter(tracker):
    results = []
    tracker.add_callback("cb", results.append)
    tracker.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
    assert len(results) == 1
    assert results[0].object_id == "obj1"


def test_callback_not_called_on_exit(tracker):
    results = []
    tracker.add_callback("cb", results.append)
    tracker.ingest(_make_event("obj1", "fence_a", EventType.EXIT))
    assert results == []


def test_remove_callback(tracker):
    results = []
    tracker.add_callback("cb", results.append)
    tracker.remove_callback("cb")
    tracker.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
    assert results == []


def test_add_non_callable_raises(tracker):
    with pytest.raises(TypeError):
        tracker.add_callback("bad", "not_a_function")


def test_all_paths_returns_all(tracker):
    tracker.ingest(_make_event("a", "f1", EventType.ENTER))
    tracker.ingest(_make_event("b", "f2", EventType.ENTER))
    paths = tracker.all_paths()
    assert set(paths.keys()) == {"a", "b"}
