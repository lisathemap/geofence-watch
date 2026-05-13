"""Tests for CorridorDetector and CorridorStream."""
from __future__ import annotations

import pytest

from geofence_watch.corridor_detector import CorridorDetector, CorridorResult
from geofence_watch.corridor_stream import CorridorStream
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    fence: str,
    etype: EventType = EventType.ENTER,
    obj: str = "truck-1",
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=obj,
        fence_name=fence,
        event_type=etype,
        point=Point(0.0, 0.0),
        timestamp=0.0,
    )


@pytest.fixture()
def detector() -> CorridorDetector:
    return CorridorDetector("route-A", ["gate-1", "gate-2", "gate-3"])


@pytest.fixture()
def stream(detector: CorridorDetector) -> CorridorStream:
    return CorridorStream(detector=detector)


# ---------------------------------------------------------------------------
# CorridorDetector – initialisation
# ---------------------------------------------------------------------------

class TestCorridorDetectorInit:
    def test_name_stored(self, detector: CorridorDetector) -> None:
        assert detector.name == "route-A"

    def test_steps_stored_as_tuple(self, detector: CorridorDetector) -> None:
        assert detector.steps == ("gate-1", "gate-2", "gate-3")

    def test_strict_default_true(self, detector: CorridorDetector) -> None:
        assert detector.strict is True

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            CorridorDetector("", ["a", "b"])

    def test_single_step_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            CorridorDetector("r", ["only-one"])


# ---------------------------------------------------------------------------
# CorridorDetector – progress tracking
# ---------------------------------------------------------------------------

class TestCorridorDetectorProgress:
    def test_non_enter_event_ignored(self, detector: CorridorDetector) -> None:
        result = detector.ingest(_make_event("gate-1", EventType.EXIT))
        assert result is None

    def test_first_step_advances(self, detector: CorridorDetector) -> None:
        result = detector.ingest(_make_event("gate-1"))
        assert result is not None
        assert result.current_step == 1
        assert result.completed is False
        assert result.deviated is False

    def test_out_of_order_fence_ignored_non_strict(self) -> None:
        det = CorridorDetector("r", ["a", "b", "c"], strict=False)
        result = det.ingest(_make_event("c"))  # skipping a and b
        assert result is None

    def test_wrong_fence_in_strict_mode_marks_deviated(self, detector: CorridorDetector) -> None:
        detector.ingest(_make_event("gate-1"))  # step 1
        result = detector.ingest(_make_event("gate-3"))  # skip gate-2
        assert result is not None
        assert result.deviated is True
        assert result.current_step == 0

    def test_completion_resets_progress(self, detector: CorridorDetector) -> None:
        detector.ingest(_make_event("gate-1"))
        detector.ingest(_make_event("gate-2"))
        result = detector.ingest(_make_event("gate-3"))
        assert result is not None
        assert result.completed is True
        # After completion progress should be reset
        assert detector.progress("truck-1") == 0

    def test_progress_returns_zero_for_unknown_object(self, detector: CorridorDetector) -> None:
        assert detector.progress("nobody") == 0

    def test_reset_clears_progress(self, detector: CorridorDetector) -> None:
        detector.ingest(_make_event("gate-1"))
        detector.reset("truck-1")
        assert detector.progress("truck-1") == 0


# ---------------------------------------------------------------------------
# CorridorStream
# ---------------------------------------------------------------------------

class TestCorridorStream:
    def test_detector_property(self, stream: CorridorStream, detector: CorridorDetector) -> None:
        assert stream.detector is detector

    def test_custom_detector_accepted(self, detector: CorridorDetector) -> None:
        s = CorridorStream(detector=detector)
        assert s.detector is detector

    def test_non_detector_raises(self) -> None:
        with pytest.raises(TypeError):
            CorridorStream(detector="not-a-detector")  # type: ignore[arg-type]

    def test_no_callbacks_initially(self, stream: CorridorStream) -> None:
        assert stream.callback_names == []

    def test_add_callback(self, stream: CorridorStream) -> None:
        stream.add_callback("cb", lambda r: None)
        assert "cb" in stream.callback_names

    def test_add_non_callable_raises(self, stream: CorridorStream) -> None:
        with pytest.raises(TypeError):
            stream.add_callback("bad", "not-callable")  # type: ignore[arg-type]

    def test_add_empty_name_raises(self, stream: CorridorStream) -> None:
        with pytest.raises(ValueError):
            stream.add_callback("", lambda r: None)

    def test_remove_callback(self, stream: CorridorStream) -> None:
        stream.add_callback("cb", lambda r: None)
        stream.remove_callback("cb")
        assert "cb" not in stream.callback_names

    def test_process_fires_callback_on_match(self, stream: CorridorStream) -> None:
        received: list[CorridorResult] = []
        stream.add_callback("rec", received.append)
        stream.process(_make_event("gate-1"))
        assert len(received) == 1
        assert received[0].current_step == 1

    def test_process_returns_none_for_non_matching(self, stream: CorridorStream) -> None:
        result = stream.process(_make_event("gate-1", EventType.EXIT))
        assert result is None

    def test_process_no_callback_when_no_result(self, stream: CorridorStream) -> None:
        fired: list[CorridorResult] = []
        stream.add_callback("cb", fired.append)
        stream.process(_make_event("gate-1", EventType.EXIT))
        assert fired == []
