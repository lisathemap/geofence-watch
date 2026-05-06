"""Tests for RateMonitor and RateStream."""

from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.rate_monitor import RateMonitor
from geofence_watch.rate_stream import RateStream


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evt(fence: str = "zone-a") -> GeofenceEvent:
    return GeofenceEvent(
        object_id="obj-1",
        fence_name=fence,
        event_type=EventType.ENTER,
        point=Point(lon=0.0, lat=0.0),
    )


# ---------------------------------------------------------------------------
# RateMonitor
# ---------------------------------------------------------------------------

class TestRateMonitorInit:
    def test_valid_window(self):
        m = RateMonitor(window_seconds=30.0)
        assert m.window_seconds == 30.0

    def test_zero_window_raises(self):
        with pytest.raises(ValueError):
            RateMonitor(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            RateMonitor(window_seconds=-5.0)


class TestRateMonitorBehaviour:
    def test_empty_count_is_zero(self):
        m = RateMonitor(window_seconds=10.0)
        assert m.count(_now=100.0) == 0

    def test_empty_rate_is_zero(self):
        m = RateMonitor(window_seconds=10.0)
        assert m.rate(_now=100.0) == 0.0

    def test_single_record_count(self):
        m = RateMonitor(window_seconds=10.0)
        m.record(_evt(), _now=100.0)
        assert m.count(_now=105.0) == 1

    def test_rate_calculation(self):
        m = RateMonitor(window_seconds=10.0)
        for i in range(5):
            m.record(_evt(), _now=100.0 + i)
        assert m.rate(_now=104.0) == pytest.approx(5 / 10.0)

    def test_old_events_evicted(self):
        m = RateMonitor(window_seconds=5.0)
        m.record(_evt(), _now=100.0)
        m.record(_evt(), _now=101.0)
        # advance past the window for the first event
        assert m.count(_now=106.0) == 1

    def test_reset_clears_all(self):
        m = RateMonitor(window_seconds=10.0)
        m.record(_evt(), _now=100.0)
        m.reset()
        assert m.count(_now=100.0) == 0


# ---------------------------------------------------------------------------
# RateStream
# ---------------------------------------------------------------------------

@pytest.fixture()
def rs() -> RateStream:
    return RateStream(window_seconds=10.0)


class TestRateStream:
    def test_default_window(self):
        s = RateStream()
        assert s.monitor.window_seconds == 60.0

    def test_feed_returns_rate(self, rs: RateStream):
        rate = rs.feed(_evt(), _now=100.0)
        assert isinstance(rate, float)
        assert rate > 0

    def test_callback_called_on_feed(self, rs: RateStream):
        results: list = []
        rs.add_callback("cb", lambda e, r: results.append((e, r)))
        rs.feed(_evt(), _now=100.0)
        assert len(results) == 1
        assert isinstance(results[0][1], float)

    def test_add_duplicate_callback_raises(self, rs: RateStream):
        rs.add_callback("cb", lambda e, r: None)
        with pytest.raises(ValueError):
            rs.add_callback("cb", lambda e, r: None)

    def test_remove_callback(self, rs: RateStream):
        rs.add_callback("cb", lambda e, r: None)
        rs.remove_callback("cb")
        assert "cb" not in rs.callback_names

    def test_remove_missing_callback_raises(self, rs: RateStream):
        with pytest.raises(KeyError):
            rs.remove_callback("ghost")

    def test_non_callable_raises(self, rs: RateStream):
        with pytest.raises(TypeError):
            rs.add_callback("bad", "not_a_function")  # type: ignore
