"""Tests for ProximityMonitor and haversine utilities."""
import math
import pytest

from geofence_watch.point import Point
from geofence_watch.fence import Geofence
from geofence_watch.proximity import (
    ProximityMonitor,
    ProximityResult,
    haversine,
    _centroid,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _square_fence(name: str, cx: float, cy: float, half: float = 0.01) -> Geofence:
    """Create a simple square Geofence centred at (cx, cy)."""
    ring = [
        [cx - half, cy - half],
        [cx + half, cy - half],
        [cx + half, cy + half],
        [cx - half, cy + half],
        [cx - half, cy - half],
    ]
    return Geofence(name=name, coordinates=[ring])


@pytest.fixture
def fence_a():
    return _square_fence("alpha", cx=0.0, cy=0.0)


@pytest.fixture
def monitor(fence_a):
    m = ProximityMonitor(threshold_m=1_000.0)
    m.register(fence_a)
    return m


# ---------------------------------------------------------------------------
# haversine
# ---------------------------------------------------------------------------

class TestHaversine:
    def test_same_point_is_zero(self):
        p = Point(lon=10.0, lat=20.0)
        assert haversine(p, p) == pytest.approx(0.0, abs=1e-6)

    def test_known_distance(self):
        # ~111 km per degree latitude
        a = Point(lon=0.0, lat=0.0)
        b = Point(lon=0.0, lat=1.0)
        assert haversine(a, b) == pytest.approx(111_195, rel=0.01)

    def test_symmetric(self):
        a = Point(lon=2.0, lat=48.0)
        b = Point(lon=3.0, lat=49.0)
        assert haversine(a, b) == pytest.approx(haversine(b, a))


# ---------------------------------------------------------------------------
# _centroid
# ---------------------------------------------------------------------------

class TestCentroid:
    def test_centroid_of_square(self, fence_a):
        c = _centroid(fence_a)
        assert c.lon == pytest.approx(0.0, abs=1e-9)
        assert c.lat == pytest.approx(0.0, abs=1e-9)

    def test_empty_ring_raises(self):
        bad = Geofence(name="empty", coordinates=[[]])
        with pytest.raises(ValueError, match="empty ring"):
            _centroid(bad)


# ---------------------------------------------------------------------------
# ProximityMonitor
# ---------------------------------------------------------------------------

class TestProximityMonitorInit:
    def test_default_threshold(self):
        m = ProximityMonitor()
        assert m.threshold_m == 500.0

    def test_custom_threshold(self):
        m = ProximityMonitor(threshold_m=200.0)
        assert m.threshold_m == 200.0

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError):
            ProximityMonitor(threshold_m=0)

    def test_negative_threshold_raises(self):
        with pytest.raises(ValueError):
            ProximityMonitor(threshold_m=-1)


class TestProximityMonitorCheck:
    def test_check_returns_one_result_per_fence(self, monitor, fence_a):
        p = Point(lon=0.0, lat=0.0)
        results = monitor.check("obj1", p)
        assert len(results) == 1

    def test_within_threshold_true_for_nearby_point(self, monitor):
        p = Point(lon=0.0, lat=0.0)  # exactly at centroid
        r = monitor.check("obj1", p)[0]
        assert r.within_threshold is True

    def test_within_threshold_false_for_distant_point(self, monitor):
        p = Point(lon=10.0, lat=10.0)
        r = monitor.check("obj1", p)[0]
        assert r.within_threshold is False

    def test_result_fields(self, monitor):
        p = Point(lon=0.0, lat=0.0)
        r = monitor.check("vehicle-7", p)[0]
        assert r.object_id == "vehicle-7"
        assert r.fence_name == "alpha"
        assert isinstance(r.distance_m, float)

    def test_no_fences_returns_empty(self):
        m = ProximityMonitor()
        assert m.check("x", Point(lon=1.0, lat=1.0)) == []

    def test_nearest_returns_closest(self):
        m = ProximityMonitor(threshold_m=10_000_000)
        m.register(_square_fence("near", 0.0, 0.0))
        m.register(_square_fence("far", 10.0, 10.0))
        p = Point(lon=0.0, lat=0.0)
        result = m.nearest("x", p)
        assert result.fence_name == "near"

    def test_nearest_no_fences_returns_none(self):
        m = ProximityMonitor()
        assert m.nearest("x", Point(lon=0.0, lat=0.0)) is None

    def test_unregister_removes_fence(self, monitor):
        monitor.unregister("alpha")
        assert monitor.fence_names == []
