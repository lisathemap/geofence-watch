"""Tests for FenceStats and FenceStatsTracker."""

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.fence_stats import FenceStats, FenceStatsTracker
from geofence_watch.point import Point


def _make_event(
    event_type: EventType,
    fence_name: str = "zone-a",
    object_id: str = "obj-1",
    timestamp: float = 0.0,
) -> GeofenceEvent:
    return GeofenceEvent(
        event_type=event_type,
        object_id=object_id,
        fence_name=fence_name,
        point=Point(lon=0.0, lat=0.0),
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# FenceStats unit tests
# ---------------------------------------------------------------------------

class TestFenceStats:
    def test_initial_counts_zero(self):
        s = FenceStats(fence_name="z")
        assert s.enter_count == 0
        assert s.exit_count == 0

    def test_average_dwell_none_when_no_exits(self):
        s = FenceStats(fence_name="z")
        assert s.average_dwell_seconds is None

    def test_total_dwell_starts_at_zero(self):
        s = FenceStats(fence_name="z")
        assert s.total_dwell_seconds == 0.0


# ---------------------------------------------------------------------------
# FenceStatsTracker tests
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker() -> FenceStatsTracker:
    return FenceStatsTracker()


def test_unknown_fence_returns_none(tracker):
    assert tracker.stats_for("missing") is None


def test_enter_increments_count(tracker):
    tracker.ingest(_make_event(EventType.ENTER, timestamp=1.0))
    assert tracker.stats_for("zone-a").enter_count == 1


def test_exit_increments_count(tracker):
    tracker.ingest(_make_event(EventType.ENTER, timestamp=1.0))
    tracker.ingest(_make_event(EventType.EXIT, timestamp=6.0))
    assert tracker.stats_for("zone-a").exit_count == 1


def test_dwell_computed_correctly(tracker):
    tracker.ingest(_make_event(EventType.ENTER, timestamp=10.0))
    tracker.ingest(_make_event(EventType.EXIT, timestamp=40.0))
    stats = tracker.stats_for("zone-a")
    assert stats.total_dwell_seconds == pytest.approx(30.0)
    assert stats.average_dwell_seconds == pytest.approx(30.0)


def test_average_dwell_across_multiple_visits(tracker):
    for enter_ts, exit_ts in [(0.0, 10.0), (20.0, 50.0)]:
        tracker.ingest(_make_event(EventType.ENTER, timestamp=enter_ts))
        tracker.ingest(_make_event(EventType.EXIT, timestamp=exit_ts))
    stats = tracker.stats_for("zone-a")
    # dwells: 10 + 30 = 40, avg = 20
    assert stats.average_dwell_seconds == pytest.approx(20.0)


def test_exit_without_matching_enter_ignored(tracker):
    tracker.ingest(_make_event(EventType.EXIT, timestamp=5.0))
    stats = tracker.stats_for("zone-a")
    assert stats.exit_count == 1
    assert stats.total_dwell_seconds == 0.0


def test_multiple_objects_tracked_independently(tracker):
    tracker.ingest(_make_event(EventType.ENTER, object_id="a", timestamp=0.0))
    tracker.ingest(_make_event(EventType.ENTER, object_id="b", timestamp=0.0))
    tracker.ingest(_make_event(EventType.EXIT, object_id="a", timestamp=5.0))
    tracker.ingest(_make_event(EventType.EXIT, object_id="b", timestamp=20.0))
    stats = tracker.stats_for("zone-a")
    assert stats.total_dwell_seconds == pytest.approx(25.0)
    assert stats.average_dwell_seconds == pytest.approx(12.5)


def test_fence_names_sorted(tracker):
    tracker.ingest(_make_event(EventType.ENTER, fence_name="beta"))
    tracker.ingest(_make_event(EventType.ENTER, fence_name="alpha"))
    assert tracker.fence_names == ("alpha", "beta")


def test_reset_single_fence(tracker):
    tracker.ingest(_make_event(EventType.ENTER, fence_name="zone-a"))
    tracker.ingest(_make_event(EventType.ENTER, fence_name="zone-b"))
    tracker.reset("zone-a")
    assert tracker.stats_for("zone-a") is None
    assert tracker.stats_for("zone-b") is not None


def test_reset_all_fences(tracker):
    tracker.ingest(_make_event(EventType.ENTER, fence_name="zone-a"))
    tracker.ingest(_make_event(EventType.ENTER, fence_name="zone-b"))
    tracker.reset()
    assert tracker.fence_names == ()
