"""Tests for ClusterDetector and ClusterStream."""
from __future__ import annotations

import pytest

from geofence_watch.cluster_detector import ClusterDetector, ClusterResult
from geofence_watch.cluster_stream import ClusterStream
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point


def _make_event(
    object_id: str,
    fence_name: str,
    event_type: EventType,
    lat: float = 0.0,
    lon: float = 0.0,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(lon=lon, lat=lat),
        timestamp=0.0,
    )


# ---------------------------------------------------------------------------
# ClusterDetector init
# ---------------------------------------------------------------------------

class TestClusterDetectorInit:
    def test_default_min_size(self):
        d = ClusterDetector()
        assert d.min_size == 2

    def test_custom_min_size(self):
        d = ClusterDetector(min_size=3)
        assert d.min_size == 3

    def test_min_size_one_raises(self):
        with pytest.raises(ValueError):
            ClusterDetector(min_size=1)

    def test_min_size_zero_raises(self):
        with pytest.raises(ValueError):
            ClusterDetector(min_size=0)


# ---------------------------------------------------------------------------
# ClusterDetector behaviour
# ---------------------------------------------------------------------------

@pytest.fixture
def detector():
    return ClusterDetector(min_size=2)


def test_single_enter_returns_none(detector):
    evt = _make_event("obj1", "zone-a", EventType.ENTER, lat=1.0, lon=1.0)
    assert detector.ingest(evt) is None


def test_two_enters_returns_cluster(detector):
    detector.ingest(_make_event("obj1", "zone-a", EventType.ENTER, lat=1.0, lon=1.0))
    result = detector.ingest(_make_event("obj2", "zone-a", EventType.ENTER, lat=2.0, lon=2.0))
    assert isinstance(result, ClusterResult)
    assert result.fence_name == "zone-a"
    assert result.size == 2
    assert "obj1" in result.object_ids
    assert "obj2" in result.object_ids


def test_centroid_is_average(detector):
    detector.ingest(_make_event("a", "z", EventType.ENTER, lat=0.0, lon=0.0))
    result = detector.ingest(_make_event("b", "z", EventType.ENTER, lat=2.0, lon=4.0))
    assert result.centroid_lat == pytest.approx(1.0)
    assert result.centroid_lon == pytest.approx(2.0)


def test_exit_drops_below_min_returns_none(detector):
    detector.ingest(_make_event("a", "z", EventType.ENTER))
    detector.ingest(_make_event("b", "z", EventType.ENTER))
    detector.ingest(_make_event("a", "z", EventType.EXIT))
    result = detector.ingest(_make_event("c", "z", EventType.ENTER, lat=1.0, lon=1.0))
    # now 2 objects again → cluster
    assert result is not None
    assert result.size == 2


def test_callback_is_called(detector):
    received = []
    detector.add_callback("cb", received.append)
    detector.ingest(_make_event("a", "z", EventType.ENTER))
    detector.ingest(_make_event("b", "z", EventType.ENTER))
    assert len(received) == 1
    assert isinstance(received[0], ClusterResult)


def test_remove_callback_stops_calls(detector):
    received = []
    detector.add_callback("cb", received.append)
    detector.remove_callback("cb")
    detector.ingest(_make_event("a", "z", EventType.ENTER))
    detector.ingest(_make_event("b", "z", EventType.ENTER))
    assert received == []


def test_non_callable_raises(detector):
    with pytest.raises(TypeError):
        detector.add_callback("bad", "not-a-function")  # type: ignore


# ---------------------------------------------------------------------------
# ClusterStream
# ---------------------------------------------------------------------------

@pytest.fixture
def stream():
    return ClusterStream(min_size=2)


class TestClusterStreamInit:
    def test_default_detector_created(self):
        s = ClusterStream()
        assert isinstance(s.detector, ClusterDetector)

    def test_custom_detector_accepted(self):
        d = ClusterDetector(min_size=3)
        s = ClusterStream(detector=d)
        assert s.detector is d

    def test_invalid_detector_raises(self):
        with pytest.raises(TypeError):
            ClusterStream(detector="bad")  # type: ignore


def test_stream_process_returns_result(stream):
    stream.process(_make_event("a", "f", EventType.ENTER))
    result = stream.process(_make_event("b", "f", EventType.ENTER))
    assert isinstance(result, ClusterResult)


def test_stream_add_remove_callback(stream):
    hits = []
    stream.add_callback("x", hits.append)
    assert "x" in stream.callback_names()
    stream.remove_callback("x")
    assert "x" not in stream.callback_names()
