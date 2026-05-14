"""Tests for SpeedStream."""
from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.speed_estimator import SpeedEstimator
from geofence_watch.speed_stream import SpeedStream


def _make_event(
    object_id: str,
    lon: float,
    lat: float,
    timestamp: float,
    fence: str = "zone-a",
) -> GeofenceEvent:
    return GeofenceEvent(
        event_type=EventType.ENTER,
        object_id=object_id,
        fence_name=fence,
        point=Point(lon=lon, lat=lat),
        timestamp=timestamp,
    )


@pytest.fixture
def stream():
    return SpeedStream()


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestSpeedStreamInit:
    def test_default_estimator_created(self, stream):
        assert isinstance(stream.estimator, SpeedEstimator)

    def test_custom_estimator_accepted(self):
        est = SpeedEstimator(min_elapsed_seconds=0.5)
        ss = SpeedStream(estimator=est)
        assert ss.estimator is est

    def test_invalid_estimator_raises(self):
        with pytest.raises(TypeError):
            SpeedStream(estimator="bad")  # type: ignore

    def test_no_callbacks_initially(self, stream):
        assert stream.callback_names == []


# ---------------------------------------------------------------------------
# Callback management
# ---------------------------------------------------------------------------

def test_add_callback(stream):
    def my_handler(s):
        pass
    stream.add_callback(my_handler)
    assert "my_handler" in stream.callback_names


def test_remove_callback(stream):
    def my_handler(s):
        pass
    stream.add_callback(my_handler)
    stream.remove_callback(my_handler)
    assert stream.callback_names == []


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

def test_first_event_no_sample(stream):
    ev = _make_event("obj1", 0.0, 0.0, 100.0)
    assert stream.process(ev) is None


def test_second_event_produces_sample(stream):
    stream.process(_make_event("obj1", 0.0, 0.0, 100.0))
    sample = stream.process(_make_event("obj1", 1.0, 0.0, 110.0))
    assert sample is not None
    assert sample.object_id == "obj1"
    assert sample.elapsed_seconds == pytest.approx(10.0)


def test_callback_receives_sample(stream):
    received = []
    stream.add_callback(received.append)
    stream.process(_make_event("obj1", 0.0, 0.0, 0.0))
    stream.process(_make_event("obj1", 0.0, 1.0, 10.0))
    assert len(received) == 1
    assert received[0].speed_mps > 0


def test_process_returns_none_for_short_elapsed():
    ss = SpeedStream(min_elapsed_seconds=1.0)
    ss.process(_make_event("obj1", 0.0, 0.0, 0.0))
    result = ss.process(_make_event("obj1", 1.0, 0.0, 0.5))  # only 0.5 s
    assert result is None
