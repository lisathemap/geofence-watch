"""Tests for SpeedEstimator and SpeedSample."""
from __future__ import annotations

import math
import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.speed_estimator import SpeedEstimator, SpeedSample


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    object_id: str,
    lon: float,
    lat: float,
    timestamp: float,
    fence: str = "zone-a",
    etype: EventType = EventType.ENTER,
) -> GeofenceEvent:
    return GeofenceEvent(
        event_type=etype,
        object_id=object_id,
        fence_name=fence,
        point=Point(lon=lon, lat=lat),
        timestamp=timestamp,
    )


# ---------------------------------------------------------------------------
# SpeedSample unit tests
# ---------------------------------------------------------------------------

class TestSpeedSample:
    def test_speed_kph_conversion(self):
        s = SpeedSample(
            object_id="obj", fence_name="f",
            speed_mps=10.0, distance_m=100.0, elapsed_seconds=10.0,
        )
        assert math.isclose(s.speed_kph, 36.0)

    def test_zero_speed(self):
        s = SpeedSample(
            object_id="obj", fence_name="f",
            speed_mps=0.0, distance_m=0.0, elapsed_seconds=5.0,
        )
        assert s.speed_kph == 0.0


# ---------------------------------------------------------------------------
# SpeedEstimator init
# ---------------------------------------------------------------------------

class TestSpeedEstimatorInit:
    def test_default_min_elapsed(self):
        est = SpeedEstimator()
        assert est._min_elapsed == 0.1

    def test_custom_min_elapsed(self):
        est = SpeedEstimator(min_elapsed_seconds=1.0)
        assert est._min_elapsed == 1.0

    def test_zero_min_elapsed_raises(self):
        with pytest.raises(ValueError):
            SpeedEstimator(min_elapsed_seconds=0)

    def test_negative_min_elapsed_raises(self):
        with pytest.raises(ValueError):
            SpeedEstimator(min_elapsed_seconds=-1.0)


# ---------------------------------------------------------------------------
# SpeedEstimator.ingest
# ---------------------------------------------------------------------------

@pytest.fixture
def est():
    return SpeedEstimator(min_elapsed_seconds=0.1)


def test_first_event_returns_none(est):
    ev = _make_event("car1", 0.0, 0.0, 1000.0)
    assert est.ingest(ev) is None


def test_second_event_returns_sample(est):
    ev1 = _make_event("car1", 0.0, 0.0, 1000.0)
    # ~111 km apart, 10 s elapsed
    ev2 = _make_event("car1", 0.0, 1.0, 1010.0)
    est.ingest(ev1)
    sample = est.ingest(ev2)
    assert sample is not None
    assert sample.object_id == "car1"
    assert sample.elapsed_seconds == pytest.approx(10.0)
    assert sample.distance_m > 100_000  # roughly 111 km


def test_elapsed_below_minimum_skipped(est):
    ev1 = _make_event("car1", 0.0, 0.0, 1000.0)
    ev2 = _make_event("car1", 0.0, 1.0, 1000.05)  # only 0.05 s
    est.ingest(ev1)
    assert est.ingest(ev2) is None


def test_callback_fired(est):
    results = []
    est.add_callback(results.append)
    est.ingest(_make_event("car1", 0.0, 0.0, 0.0))
    est.ingest(_make_event("car1", 1.0, 0.0, 5.0))
    assert len(results) == 1


def test_separate_objects_independent(est):
    est.ingest(_make_event("a", 0.0, 0.0, 0.0))
    est.ingest(_make_event("b", 0.0, 0.0, 0.0))
    # second event for each — both should produce samples
    s_a = est.ingest(_make_event("a", 1.0, 0.0, 5.0))
    s_b = est.ingest(_make_event("b", 0.0, 1.0, 5.0))
    assert s_a is not None
    assert s_b is not None


def test_reset_single_object(est):
    est.ingest(_make_event("car1", 0.0, 0.0, 0.0))
    est.reset("car1")
    assert est.ingest(_make_event("car1", 1.0, 0.0, 5.0)) is None


def test_reset_all(est):
    est.ingest(_make_event("a", 0.0, 0.0, 0.0))
    est.ingest(_make_event("b", 0.0, 0.0, 0.0))
    est.reset()
    assert est.ingest(_make_event("a", 1.0, 0.0, 5.0)) is None
    assert est.ingest(_make_event("b", 0.0, 1.0, 5.0)) is None


def test_remove_callback(est):
    results = []
    est.add_callback(results.append)
    est.remove_callback(results.append)
    est.ingest(_make_event("car1", 0.0, 0.0, 0.0))
    est.ingest(_make_event("car1", 1.0, 0.0, 5.0))
    assert results == []


def test_add_non_callable_raises(est):
    with pytest.raises(TypeError):
        est.add_callback("not_a_function")  # type: ignore
