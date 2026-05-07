"""Tests for BoundaryCrossingTracker and CrossingRecord."""
from __future__ import annotations

import datetime
import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.boundary_crossings import BoundaryCrossingTracker, CrossingRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = datetime.datetime(2024, 1, 1, 12, 0, 0)


def _make_event(
    event_type: EventType,
    object_id: str = "obj-1",
    fence_name: str = "zone-a",
) -> GeofenceEvent:
    return GeofenceEvent(
        event_type=event_type,
        object_id=object_id,
        fence_name=fence_name,
        point=Point(lon=0.0, lat=0.0),
        timestamp=_TS,
    )


# ---------------------------------------------------------------------------
# CrossingRecord unit tests
# ---------------------------------------------------------------------------

class TestCrossingRecord:
    def test_total_is_sum(self):
        rec = CrossingRecord(object_id="a", fence_name="f", enter_count=3, exit_count=2)
        assert rec.total == 5

    def test_zero_initial_counts(self):
        rec = CrossingRecord(object_id="a", fence_name="f")
        assert rec.enter_count == 0
        assert rec.exit_count == 0
        assert rec.total == 0


# ---------------------------------------------------------------------------
# BoundaryCrossingTracker init
# ---------------------------------------------------------------------------

class TestTrackerInit:
    def test_default_no_max_history(self):
        t = BoundaryCrossingTracker()
        assert t._max_history is None

    def test_positive_max_history_accepted(self):
        t = BoundaryCrossingTracker(max_history=5)
        assert t._max_history == 5

    def test_zero_max_history_raises(self):
        with pytest.raises(ValueError):
            BoundaryCrossingTracker(max_history=0)

    def test_negative_max_history_raises(self):
        with pytest.raises(ValueError):
            BoundaryCrossingTracker(max_history=-1)


# ---------------------------------------------------------------------------
# Ingestion behaviour
# ---------------------------------------------------------------------------

@pytest.fixture()
def tracker() -> BoundaryCrossingTracker:
    return BoundaryCrossingTracker()


def test_enter_increments_enter_count(tracker):
    tracker.ingest(_make_event(EventType.ENTER))
    rec = tracker.record_for("obj-1", "zone-a")
    assert rec is not None
    assert rec.enter_count == 1
    assert rec.exit_count == 0


def test_exit_increments_exit_count(tracker):
    tracker.ingest(_make_event(EventType.EXIT))
    rec = tracker.record_for("obj-1", "zone-a")
    assert rec.exit_count == 1
    assert rec.enter_count == 0


def test_inside_event_ignored(tracker):
    tracker.ingest(_make_event(EventType.INSIDE))
    assert tracker.record_for("obj-1", "zone-a") is None


def test_multiple_crossings_accumulate(tracker):
    for _ in range(3):
        tracker.ingest(_make_event(EventType.ENTER))
    tracker.ingest(_make_event(EventType.EXIT))
    rec = tracker.record_for("obj-1", "zone-a")
    assert rec.enter_count == 3
    assert rec.exit_count == 1
    assert rec.total == 4


def test_different_objects_tracked_separately(tracker):
    tracker.ingest(_make_event(EventType.ENTER, object_id="obj-1"))
    tracker.ingest(_make_event(EventType.ENTER, object_id="obj-2"))
    tracker.ingest(_make_event(EventType.ENTER, object_id="obj-2"))
    assert tracker.record_for("obj-1", "zone-a").enter_count == 1
    assert tracker.record_for("obj-2", "zone-a").enter_count == 2


def test_different_fences_tracked_separately(tracker):
    tracker.ingest(_make_event(EventType.ENTER, fence_name="zone-a"))
    tracker.ingest(_make_event(EventType.EXIT, fence_name="zone-b"))
    assert tracker.record_for("obj-1", "zone-a").enter_count == 1
    assert tracker.record_for("obj-1", "zone-b").exit_count == 1


def test_record_for_unknown_returns_none(tracker):
    assert tracker.record_for("unknown", "nowhere") is None


def test_all_records_sorted(tracker):
    tracker.ingest(_make_event(EventType.ENTER, object_id="b", fence_name="z"))
    tracker.ingest(_make_event(EventType.ENTER, object_id="a", fence_name="z"))
    records = tracker.all_records()
    assert records[0].object_id == "a"
    assert records[1].object_id == "b"


def test_events_for_returns_log(tracker):
    tracker.ingest(_make_event(EventType.ENTER))
    tracker.ingest(_make_event(EventType.EXIT))
    events = tracker.events_for("obj-1", "zone-a")
    assert len(events) == 2
    assert events[0].event_type is EventType.ENTER
    assert events[1].event_type is EventType.EXIT


def test_max_history_trims_log():
    tracker = BoundaryCrossingTracker(max_history=2)
    for _ in range(5):
        tracker.ingest(_make_event(EventType.ENTER))
    assert len(tracker.events_for("obj-1", "zone-a")) == 2


def test_reset_clears_all(tracker):
    tracker.ingest(_make_event(EventType.ENTER))
    tracker.reset()
    assert tracker.all_records() == []
    assert tracker.events_for("obj-1", "zone-a") == []


# ---------------------------------------------------------------------------
# Callback behaviour
# ---------------------------------------------------------------------------

def test_callback_invoked_on_crossing(tracker):
    received = []
    tracker.add_callback(received.append)
    tracker.ingest(_make_event(EventType.ENTER))
    assert len(received) == 1
    assert isinstance(received[0], CrossingRecord)


def test_callback_not_invoked_for_inside(tracker):
    received = []
    tracker.add_callback(received.append)
    tracker.ingest(_make_event(EventType.INSIDE))
    assert received == []


def test_add_non_callable_raises(tracker):
    with pytest.raises(TypeError):
        tracker.add_callback("not-callable")  # type: ignore[arg-type]


def test_remove_callback(tracker):
    received = []
    tracker.add_callback(received.append)
    tracker.remove_callback(received.append)
    tracker.ingest(_make_event(EventType.ENTER))
    assert received == []


def test_duplicate_add_ignored(tracker):
    cb = lambda r: None  # noqa: E731
    tracker.add_callback(cb)
    tracker.add_callback(cb)
    assert tracker.callback_count == 1
