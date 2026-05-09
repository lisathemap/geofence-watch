"""Tests for DriftDetector and DriftStream."""
from __future__ import annotations

import pytest

from geofence_watch.drift_detector import DriftDetector, DriftResult
from geofence_watch.drift_stream import DriftStream
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ANCHOR = Point(lon=0.0, lat=0.0)
NEARBY = Point(lon=0.001, lat=0.001)   # ~157 m from anchor
FAR    = Point(lon=0.01,  lat=0.01)    # ~1570 m from anchor


def _make_event(object_id: str, point: Point) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name="test-fence",
        event_type=EventType.ENTER,
        point=point,
    )


# ---------------------------------------------------------------------------
# DriftDetector – initialisation
# ---------------------------------------------------------------------------

class TestDriftDetectorInit:
    def test_default_threshold_stored(self):
        d = DriftDetector(threshold_m=200.0)
        assert d._default_threshold == 200.0

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError):
            DriftDetector(threshold_m=0)

    def test_negative_threshold_raises(self):
        with pytest.raises(ValueError):
            DriftDetector(threshold_m=-100)

    def test_no_tracked_objects_initially(self):
        d = DriftDetector()
        assert d.tracked_objects == []


# ---------------------------------------------------------------------------
# DriftDetector – anchor management
# ---------------------------------------------------------------------------

class TestAnchorManagement:
    def test_set_anchor_tracks_object(self):
        d = DriftDetector()
        d.set_anchor("obj1", ANCHOR)
        assert "obj1" in d.tracked_objects

    def test_set_anchor_custom_threshold(self):
        d = DriftDetector(threshold_m=500)
        d.set_anchor("obj1", ANCHOR, threshold_m=100.0)
        assert d._thresholds["obj1"] == 100.0

    def test_set_anchor_default_threshold_used_when_none(self):
        d = DriftDetector(threshold_m=300.0)
        d.set_anchor("obj1", ANCHOR)
        assert d._thresholds["obj1"] == 300.0

    def test_remove_anchor(self):
        d = DriftDetector()
        d.set_anchor("obj1", ANCHOR)
        d.remove_anchor("obj1")
        assert "obj1" not in d.tracked_objects

    def test_remove_nonexistent_anchor_ok(self):
        d = DriftDetector()
        d.remove_anchor("ghost")  # should not raise


# ---------------------------------------------------------------------------
# DriftDetector – check logic
# ---------------------------------------------------------------------------

class TestDriftCheck:
    def test_returns_none_without_anchor(self):
        d = DriftDetector()
        result = d.check("unknown", NEARBY)
        assert result is None

    def test_no_drift_when_nearby(self):
        d = DriftDetector(threshold_m=500.0)
        d.set_anchor("obj1", ANCHOR)
        result = d.check("obj1", NEARBY)
        assert result is not None
        assert result.drifted is False

    def test_drift_when_far(self):
        d = DriftDetector(threshold_m=500.0)
        d.set_anchor("obj1", ANCHOR)
        result = d.check("obj1", FAR)
        assert result is not None
        assert result.drifted is True

    def test_result_fields_populated(self):
        d = DriftDetector(threshold_m=500.0)
        d.set_anchor("obj1", ANCHOR)
        result = d.check("obj1", NEARBY)
        assert result.object_id == "obj1"
        assert result.anchor == ANCHOR
        assert result.current == NEARBY
        assert result.threshold_m == 500.0
        assert result.distance_m > 0

    def test_callback_invoked(self):
        received: list[DriftResult] = []
        d = DriftDetector(threshold_m=500.0)
        d.set_anchor("obj1", ANCHOR)
        d.add_callback(received.append)
        d.check("obj1", FAR)
        assert len(received) == 1
        assert received[0].drifted is True

    def test_ingest_uses_event_fields(self):
        d = DriftDetector(threshold_m=500.0)
        d.set_anchor("obj1", ANCHOR)
        evt = _make_event("obj1", FAR)
        result = d.ingest(evt)
        assert result is not None
        assert result.object_id == "obj1"


# ---------------------------------------------------------------------------
# DriftStream
# ---------------------------------------------------------------------------

class TestDriftStream:
    def test_default_detector_created(self):
        ds = DriftStream()
        assert isinstance(ds.detector, DriftDetector)

    def test_custom_detector_accepted(self):
        det = DriftDetector(threshold_m=100.0)
        ds = DriftStream(detector=det)
        assert ds.detector is det

    def test_process_returns_none_without_anchor(self):
        ds = DriftStream()
        evt = _make_event("obj1", NEARBY)
        assert ds.process(evt) is None

    def test_process_triggers_callback(self):
        received: list[DriftResult] = []
        ds = DriftStream()
        ds.set_anchor("obj1", ANCHOR, threshold_m=50.0)
        ds.add_callback(received.append)
        ds.process(_make_event("obj1", FAR))
        assert len(received) == 1

    def test_add_non_callable_raises(self):
        ds = DriftStream()
        with pytest.raises(TypeError):
            ds.add_callback("not-a-function")  # type: ignore

    def test_remove_callback(self):
        received: list[DriftResult] = []
        ds = DriftStream()
        ds.set_anchor("obj1", ANCHOR, threshold_m=50.0)
        ds.add_callback(received.append)
        ds.remove_callback(received.append)
        ds.process(_make_event("obj1", FAR))
        assert received == []

    def test_callback_names(self):
        def my_handler(r: DriftResult) -> None: ...
        ds = DriftStream()
        ds.add_callback(my_handler)
        assert "my_handler" in ds.callback_names

    def test_remove_anchor_delegated(self):
        ds = DriftStream()
        ds.set_anchor("obj1", ANCHOR)
        ds.remove_anchor("obj1")
        assert "obj1" not in ds.detector.tracked_objects
