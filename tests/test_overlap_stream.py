"""Tests for OverlapStream."""
from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.overlap_detector import OverlapDetector
from geofence_watch.overlap_stream import OverlapStream
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


@pytest.fixture
def stream() -> OverlapStream:
    return OverlapStream()


class TestOverlapStreamInit:
    def test_default_detector_created(self, stream):
        assert isinstance(stream.detector, OverlapDetector)

    def test_custom_detector_accepted(self):
        d = OverlapDetector(min_overlap=3)
        s = OverlapStream(detector=d)
        assert s.detector is d

    def test_no_callbacks_initially(self, stream):
        assert stream.callback_names() == []


def test_add_and_remove_callback(stream):
    stream.add_callback("x", lambda r: None)
    assert "x" in stream.callback_names()
    stream.remove_callback("x")
    assert "x" not in stream.callback_names()


def test_process_returns_none_single_enter(stream):
    ev = _make_event("obj1", "fence_a", EventType.ENTER)
    assert stream.process(ev) is None


def test_process_returns_result_on_overlap(stream):
    stream.process(_make_event("obj1", "fence_a", EventType.ENTER))
    result = stream.process(_make_event("obj1", "fence_b", EventType.ENTER))
    assert result is not None
    assert result.object_id == "obj1"


def test_callback_invoked_via_process(stream):
    received = []
    stream.add_callback("cb", received.append)
    stream.process(_make_event("obj1", "fence_a", EventType.ENTER))
    stream.process(_make_event("obj1", "fence_b", EventType.ENTER))
    assert len(received) == 1


def test_active_fences_delegated(stream):
    stream.process(_make_event("obj1", "fence_a", EventType.ENTER))
    assert "fence_a" in stream.active_fences("obj1")


def test_reset_delegated(stream):
    stream.process(_make_event("obj1", "fence_a", EventType.ENTER))
    stream.reset("obj1")
    assert stream.active_fences("obj1") == frozenset()
