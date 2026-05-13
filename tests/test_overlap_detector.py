"""Tests for OverlapDetector and OverlapResult."""
from __future__ import annotations

import time
import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.overlap_detector import OverlapDetector, OverlapResult
from geofence_watch.point import Point


def _make_event(
    object_id: str,
    fence_name: str,
    event_type: EventType,
    ts: float = 1000.0,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(lon=0.0, lat=0.0),
        timestamp=ts,
    )


# ---------------------------------------------------------------------------
# OverlapResult
# ---------------------------------------------------------------------------

class TestOverlapResult:
    def test_fields_stored(self):
        r = OverlapResult(object_id="a", fence_names=frozenset({"f1", "f2"}), timestamp=5.0)
        assert r.object_id == "a"
        assert r.fence_names == frozenset({"f1", "f2"})
        assert r.timestamp == 5.0


# ---------------------------------------------------------------------------
# OverlapDetector init
# ---------------------------------------------------------------------------

class TestOverlapDetectorInit:
    def test_default_min_overlap(self):
        d = OverlapDetector()
        assert d.min_overlap == 2

    def test_custom_min_overlap(self):
        d = OverlapDetector(min_overlap=3)
        assert d.min_overlap == 3

    def test_min_overlap_one_raises(self):
        with pytest.raises(ValueError):
            OverlapDetector(min_overlap=1)

    def test_min_overlap_zero_raises(self):
        with pytest.raises(ValueError):
            OverlapDetector(min_overlap=0)


# ---------------------------------------------------------------------------
# Ingestion logic
# ---------------------------------------------------------------------------

@pytest.fixture
def detector():
    return OverlapDetector(min_overlap=2)


def test_single_enter_no_overlap(detector):
    ev = _make_event("obj1", "fence_a", EventType.ENTER)
    result = detector.ingest(ev)
    assert result is None


def test_two_enters_triggers_overlap(detector):
    detector.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
    result = detector.ingest(_make_event("obj1", "fence_b", EventType.ENTER))
    assert result is not None
    assert result.object_id == "obj1"
    assert "fence_a" in result.fence_names
    assert "fence_b" in result.fence_names


def test_exit_removes_fence_clears_overlap(detector):
    detector.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
    detector.ingest(_make_event("obj1", "fence_b", EventType.ENTER))
    result = detector.ingest(_make_event("obj1", "fence_b", EventType.EXIT))
    assert result is None


def test_different_objects_independent(detector):
    detector.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
    result = detector.ingest(_make_event("obj2", "fence_b", EventType.ENTER))
    assert result is None


def test_callback_fired_on_overlap(detector):
    fired = []
    detector.add_callback("cb", fired.append)
    detector.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
    detector.ingest(_make_event("obj1", "fence_b", EventType.ENTER))
    assert len(fired) == 1
    assert fired[0].object_id == "obj1"


def test_add_non_callable_raises(detector):
    with pytest.raises(TypeError):
        detector.add_callback("bad", "not_a_function")  # type: ignore


def test_remove_callback(detector):
    fired = []
    detector.add_callback("cb", fired.append)
    detector.remove_callback("cb")
    detector.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
    detector.ingest(_make_event("obj1", "fence_b", EventType.ENTER))
    assert fired == []


def test_active_fences_reflects_state(detector):
    detector.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
    detector.ingest(_make_event("obj1", "fence_b", EventType.ENTER))
    assert detector.active_fences("obj1") == frozenset({"fence_a", "fence_b"})


def test_reset_single_object(detector):
    detector.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
    detector.reset("obj1")
    assert detector.active_fences("obj1") == frozenset()


def test_reset_all(detector):
    detector.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
    detector.ingest(_make_event("obj2", "fence_b", EventType.ENTER))
    detector.reset()
    assert detector.active_fences("obj1") == frozenset()
    assert detector.active_fences("obj2") == frozenset()


def test_min_overlap_three(detector):
    d = OverlapDetector(min_overlap=3)
    d.ingest(_make_event("obj1", "f1", EventType.ENTER))
    d.ingest(_make_event("obj1", "f2", EventType.ENTER))
    result_two = d.ingest(_make_event("obj1", "f2", EventType.ENTER))  # duplicate key
    # still only 2 unique fences
    assert result_two is None
    result_three = d.ingest(_make_event("obj1", "f3", EventType.ENTER))
    assert result_three is not None
    assert len(result_three.fence_names) == 3
