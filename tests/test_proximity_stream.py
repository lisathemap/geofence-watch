"""Tests for ProximityStream."""
import pytest

from geofence_watch.point import Point
from geofence_watch.fence import Geofence
from geofence_watch.proximity import ProximityResult
from geofence_watch.proximity_stream import ProximityStream


def _square_fence(name: str, cx: float = 0.0, cy: float = 0.0, half: float = 0.01) -> Geofence:
    ring = [
        [cx - half, cy - half],
        [cx + half, cy - half],
        [cx + half, cy + half],
        [cx - half, cy + half],
        [cx - half, cy - half],
    ]
    return Geofence(name=name, coordinates=[ring])


@pytest.fixture
def stream():
    ps = ProximityStream(threshold_m=1_000.0)
    ps.register_fence(_square_fence("zone-1"))
    return ps


class TestProximityStreamInit:
    def test_monitor_property(self, stream):
        from geofence_watch.proximity import ProximityMonitor
        assert isinstance(stream.monitor, ProximityMonitor)

    def test_no_callbacks_initially(self, stream):
        assert stream.callback_names == []


class TestProximityStreamCallbacks:
    def test_add_callback(self, stream):
        stream.add_callback("cb1", lambda r: None)
        assert "cb1" in stream.callback_names

    def test_remove_callback(self, stream):
        stream.add_callback("cb1", lambda r: None)
        stream.remove_callback("cb1")
        assert "cb1" not in stream.callback_names

    def test_add_non_callable_raises(self, stream):
        with pytest.raises(TypeError):
            stream.add_callback("bad", "not-a-function")

    def test_callback_receives_results(self, stream):
        received = []
        stream.add_callback("collector", received.extend)
        p = Point(lon=0.0, lat=0.0)
        stream.process("obj1", p)
        assert len(received) == 1
        assert isinstance(received[0], ProximityResult)

    def test_multiple_callbacks_all_called(self, stream):
        counts = {"a": 0, "b": 0}
        stream.add_callback("a", lambda r: counts.__setitem__("a", counts["a"] + 1))
        stream.add_callback("b", lambda r: counts.__setitem__("b", counts["b"] + 1))
        stream.process("obj", Point(lon=0.0, lat=0.0))
        assert counts["a"] == 1
        assert counts["b"] == 1


class TestProximityStreamProcess:
    def test_process_returns_list(self, stream):
        results = stream.process("v1", Point(lon=0.0, lat=0.0))
        assert isinstance(results, list)

    def test_process_result_count_matches_fences(self, stream):
        stream.register_fence(_square_fence("zone-2", cx=5.0, cy=5.0))
        results = stream.process("v1", Point(lon=0.0, lat=0.0))
        assert len(results) == 2

    def test_nearest_no_callbacks_fired(self, stream):
        fired = []
        stream.add_callback("spy", fired.append)
        stream.nearest("v1", Point(lon=0.0, lat=0.0))
        assert fired == []

    def test_nearest_returns_proximity_result(self, stream):
        r = stream.nearest("v1", Point(lon=0.0, lat=0.0))
        assert isinstance(r, ProximityResult)

    def test_unregister_fence(self, stream):
        stream.unregister_fence("zone-1")
        results = stream.process("v1", Point(lon=0.0, lat=0.0))
        assert results == []
