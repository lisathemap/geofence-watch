"""Tests for geofence_watch.aggregator."""

from datetime import datetime, timedelta

import pytest

from geofence_watch.aggregator import EventAggregator, WindowSummary
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE = datetime(2024, 6, 1, 12, 0, 0)


def _evt(
    object_id: str,
    fence_name: str,
    event_type: EventType,
    offset_seconds: float = 0,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        timestamp=BASE + timedelta(seconds=offset_seconds),
        point=Point(lon=0.0, lat=0.0),
    )


# ---------------------------------------------------------------------------
# EventAggregator construction
# ---------------------------------------------------------------------------


class TestEventAggregatorInit:
    def test_default_no_window(self):
        agg = EventAggregator()
        assert agg._window is None

    def test_positive_window_accepted(self):
        agg = EventAggregator(window_seconds=300)
        assert agg._window == 300

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="positive"):
            EventAggregator(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="positive"):
            EventAggregator(window_seconds=-10)


# ---------------------------------------------------------------------------
# Ingest / clear
# ---------------------------------------------------------------------------


class TestIngest:
    def test_ingest_single(self):
        agg = EventAggregator()
        agg.ingest(_evt("obj1", "zone_a", EventType.ENTER))
        assert agg.event_count == 1

    def test_ingest_many(self):
        agg = EventAggregator()
        evts = [_evt("obj1", "zone_a", EventType.ENTER, i) for i in range(5)]
        agg.ingest_many(evts)
        assert agg.event_count == 5

    def test_clear_resets_count(self):
        agg = EventAggregator()
        agg.ingest(_evt("obj1", "zone_a", EventType.ENTER))
        agg.clear()
        assert agg.event_count == 0


# ---------------------------------------------------------------------------
# Summarise — counts
# ---------------------------------------------------------------------------


class TestSummariseCounts:
    def test_enter_counted(self):
        agg = EventAggregator()
        agg.ingest(_evt("obj1", "zone_a", EventType.ENTER))
        s = agg.summarise(now=BASE + timedelta(seconds=1))
        assert s["obj1:zone_a"].enter_count == 1
        assert s["obj1:zone_a"].exit_count == 0

    def test_exit_counted(self):
        agg = EventAggregator()
        agg.ingest(_evt("obj1", "zone_a", EventType.ENTER))
        agg.ingest(_evt("obj1", "zone_a", EventType.EXIT, offset_seconds=60))
        s = agg.summarise(now=BASE + timedelta(seconds=120))
        assert s["obj1:zone_a"].exit_count == 1

    def test_multiple_objects_separate_keys(self):
        agg = EventAggregator()
        agg.ingest(_evt("obj1", "zone_a", EventType.ENTER))
        agg.ingest(_evt("obj2", "zone_a", EventType.ENTER))
        s = agg.summarise(now=BASE + timedelta(seconds=1))
        assert "obj1:zone_a" in s
        assert "obj2:zone_a" in s


# ---------------------------------------------------------------------------
# Summarise — dwell time
# ---------------------------------------------------------------------------


class TestSummariseDwell:
    def test_dwell_computed_on_exit(self):
        agg = EventAggregator()
        agg.ingest(_evt("obj1", "zone_a", EventType.ENTER, 0))
        agg.ingest(_evt("obj1", "zone_a", EventType.EXIT, 100))
        s = agg.summarise(now=BASE + timedelta(seconds=200))
        assert s["obj1:zone_a"].dwell_seconds == pytest.approx(100.0)

    def test_open_dwell_accumulates_to_now(self):
        agg = EventAggregator()
        agg.ingest(_evt("obj1", "zone_a", EventType.ENTER, 0))
        now = BASE + timedelta(seconds=50)
        s = agg.summarise(now=now)
        assert s["obj1:zone_a"].dwell_seconds == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Summarise — window filtering
# ---------------------------------------------------------------------------


class TestWindowFiltering:
    def test_old_events_excluded(self):
        agg = EventAggregator(window_seconds=60)
        # This event is 120 s old — outside the 60-s window
        agg.ingest(_evt("obj1", "zone_a", EventType.ENTER, 0))
        now = BASE + timedelta(seconds=120)
        s = agg.summarise(now=now)
        assert "obj1:zone_a" not in s

    def test_recent_events_included(self):
        agg = EventAggregator(window_seconds=300)
        agg.ingest(_evt("obj1", "zone_a", EventType.ENTER, 0))
        now = BASE + timedelta(seconds=100)
        s = agg.summarise(now=now)
        assert "obj1:zone_a" in s

    def test_no_window_includes_all(self):
        agg = EventAggregator()
        agg.ingest(_evt("obj1", "zone_a", EventType.ENTER, 0))
        now = BASE + timedelta(days=365)
        s = agg.summarise(now=now)
        assert "obj1:zone_a" in s
