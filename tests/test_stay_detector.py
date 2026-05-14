"""Tests for StayDetector and StayStream."""
from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.stay_detector import StayDetector, StayResult
from geofence_watch.stay_stream import StayStream


class _FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_event(etype: EventType, obj: str = "obj1", fence: str = "zone_a") -> GeofenceEvent:
    return GeofenceEvent(
        event_type=etype,
        object_id=obj,
        fence_name=fence,
        point=Point(lon=0.0, lat=0.0),
        timestamp=0.0,
    )


# ---------------------------------------------------------------------------
# StayDetector init
# ---------------------------------------------------------------------------

def test_default_min_seconds():
    d = StayDetector()
    assert d.min_seconds == 60.0


def test_custom_min_seconds():
    d = StayDetector(min_seconds=30.0)
    assert d.min_seconds == 30.0


def test_zero_min_seconds_raises():
    with pytest.raises(ValueError):
        StayDetector(min_seconds=0)


def test_negative_min_seconds_raises():
    with pytest.raises(ValueError):
        StayDetector(min_seconds=-5)


# ---------------------------------------------------------------------------
# StayDetector behaviour
# ---------------------------------------------------------------------------

def test_enter_returns_none():
    clock = _FakeClock()
    d = StayDetector(min_seconds=10.0, clock=clock)
    result = d.ingest(_make_event(EventType.ENTER))
    assert result is None


def test_exit_below_threshold_returns_none():
    clock = _FakeClock()
    d = StayDetector(min_seconds=30.0, clock=clock)
    d.ingest(_make_event(EventType.ENTER))
    clock.advance(20.0)
    result = d.ingest(_make_event(EventType.EXIT))
    assert result is None


def test_exit_above_threshold_returns_result():
    clock = _FakeClock()
    d = StayDetector(min_seconds=30.0, clock=clock)
    d.ingest(_make_event(EventType.ENTER))
    clock.advance(45.0)
    result = d.ingest(_make_event(EventType.EXIT))
    assert isinstance(result, StayResult)
    assert result.duration_seconds == pytest.approx(45.0)
    assert result.object_id == "obj1"
    assert result.fence_name == "zone_a"


def test_callback_fired_on_stay():
    clock = _FakeClock()
    d = StayDetector(min_seconds=10.0, clock=clock)
    received = []
    d.add_callback("cb", received.append)
    d.ingest(_make_event(EventType.ENTER))
    clock.advance(20.0)
    d.ingest(_make_event(EventType.EXIT))
    assert len(received) == 1
    assert received[0].duration_seconds == pytest.approx(20.0)


def test_callback_not_fired_below_threshold():
    clock = _FakeClock()
    d = StayDetector(min_seconds=10.0, clock=clock)
    received = []
    d.add_callback("cb", received.append)
    d.ingest(_make_event(EventType.ENTER))
    clock.advance(5.0)
    d.ingest(_make_event(EventType.EXIT))
    assert received == []


def test_exit_without_enter_returns_none():
    clock = _FakeClock()
    d = StayDetector(min_seconds=10.0, clock=clock)
    result = d.ingest(_make_event(EventType.EXIT))
    assert result is None


def test_active_count_tracks_entries():
    clock = _FakeClock()
    d = StayDetector(min_seconds=10.0, clock=clock)
    assert d.active_count() == 0
    d.ingest(_make_event(EventType.ENTER, obj="a"))
    d.ingest(_make_event(EventType.ENTER, obj="b"))
    assert d.active_count() == 2
    clock.advance(20.0)
    d.ingest(_make_event(EventType.EXIT, obj="a"))
    assert d.active_count() == 1


def test_reset_clears_entries():
    clock = _FakeClock()
    d = StayDetector(min_seconds=10.0, clock=clock)
    d.ingest(_make_event(EventType.ENTER))
    d.reset()
    assert d.active_count() == 0


def test_remove_callback():
    clock = _FakeClock()
    d = StayDetector(min_seconds=5.0, clock=clock)
    received = []
    d.add_callback("cb", received.append)
    d.remove_callback("cb")
    d.ingest(_make_event(EventType.ENTER))
    clock.advance(10.0)
    d.ingest(_make_event(EventType.EXIT))
    assert received == []


# ---------------------------------------------------------------------------
# StayStream
# ---------------------------------------------------------------------------

@pytest.fixture
def stream():
    clock = _FakeClock()
    detector = StayDetector(min_seconds=20.0, clock=clock)
    s = StayStream(detector=detector)
    s._clock = clock  # expose for tests
    return s


def test_default_detector_created():
    s = StayStream()
    assert isinstance(s.detector, StayDetector)


def test_custom_detector_accepted():
    d = StayDetector(min_seconds=5.0)
    s = StayStream(detector=d)
    assert s.detector is d


def test_invalid_detector_raises():
    with pytest.raises(TypeError):
        StayStream(detector="bad")


def test_process_non_event_raises():
    s = StayStream()
    with pytest.raises(TypeError):
        s.process("not-an-event")


def test_stream_process_returns_result():
    clock = _FakeClock()
    d = StayDetector(min_seconds=10.0, clock=clock)
    s = StayStream(detector=d)
    s.process(_make_event(EventType.ENTER))
    clock.advance(15.0)
    result = s.process(_make_event(EventType.EXIT))
    assert isinstance(result, StayResult)


def test_stream_add_remove_callback():
    s = StayStream()
    s.add_callback("x", lambda r: None)
    assert "x" in s.callback_names
    s.remove_callback("x")
    assert "x" not in s.callback_names
