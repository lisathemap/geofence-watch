"""Tests for SequenceDetector and SequenceMatch."""
from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.sequence_detector import SequenceDetector, SequenceMatch


def _make_event(
    object_id: str,
    fence_name: str,
    event_type: EventType,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(0.0, 0.0),
    )


PATTERN = [
    ("zone_a", EventType.ENTER),
    ("zone_b", EventType.ENTER),
    ("zone_b", EventType.EXIT),
]


@pytest.fixture()
def detector() -> SequenceDetector:
    return SequenceDetector(PATTERN)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestSequenceDetectorInit:
    def test_empty_pattern_raises(self):
        with pytest.raises(ValueError):
            SequenceDetector([])

    def test_pattern_stored_as_tuple(self, detector):
        assert isinstance(detector.pattern, tuple)
        assert len(detector.pattern) == 3

    def test_initial_progress_zero(self, detector):
        assert detector.progress("obj1") == 0


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

class TestSequenceDetectorMatching:
    def test_full_match_fires_callback(self, detector):
        results = []
        detector.add_callback(results.append)

        detector.feed(_make_event("o1", "zone_a", EventType.ENTER))
        detector.feed(_make_event("o1", "zone_b", EventType.ENTER))
        detector.feed(_make_event("o1", "zone_b", EventType.EXIT))

        assert len(results) == 1
        assert isinstance(results[0], SequenceMatch)
        assert results[0].object_id == "o1"
        assert len(results[0].events) == 3

    def test_partial_match_no_callback(self, detector):
        results = []
        detector.add_callback(results.append)

        detector.feed(_make_event("o1", "zone_a", EventType.ENTER))
        detector.feed(_make_event("o1", "zone_b", EventType.ENTER))

        assert results == []
        assert detector.progress("o1") == 2

    def test_mismatch_resets_progress(self, detector):
        detector.feed(_make_event("o1", "zone_a", EventType.ENTER))
        assert detector.progress("o1") == 1

        detector.feed(_make_event("o1", "zone_c", EventType.ENTER))  # wrong
        assert detector.progress("o1") == 0

    def test_no_reset_on_mismatch_option(self):
        det = SequenceDetector(PATTERN, reset_on_mismatch=False)
        det.feed(_make_event("o1", "zone_a", EventType.ENTER))
        det.feed(_make_event("o1", "zone_c", EventType.ENTER))  # wrong
        assert det.progress("o1") == 1  # progress kept

    def test_independent_objects(self, detector):
        results = []
        detector.add_callback(results.append)

        detector.feed(_make_event("o1", "zone_a", EventType.ENTER))
        detector.feed(_make_event("o2", "zone_a", EventType.ENTER))

        assert detector.progress("o1") == 1
        assert detector.progress("o2") == 1
        assert results == []

    def test_progress_reset_after_match(self, detector):
        detector.feed(_make_event("o1", "zone_a", EventType.ENTER))
        detector.feed(_make_event("o1", "zone_b", EventType.ENTER))
        detector.feed(_make_event("o1", "zone_b", EventType.EXIT))
        assert detector.progress("o1") == 0

    def test_manual_reset_single(self, detector):
        detector.feed(_make_event("o1", "zone_a", EventType.ENTER))
        detector.reset("o1")
        assert detector.progress("o1") == 0

    def test_manual_reset_all(self, detector):
        detector.feed(_make_event("o1", "zone_a", EventType.ENTER))
        detector.feed(_make_event("o2", "zone_a", EventType.ENTER))
        detector.reset()
        assert detector.progress("o1") == 0
        assert detector.progress("o2") == 0

    def test_remove_callback(self, detector):
        results = []
        detector.add_callback(results.append)
        detector.remove_callback(results.append)

        detector.feed(_make_event("o1", "zone_a", EventType.ENTER))
        detector.feed(_make_event("o1", "zone_b", EventType.ENTER))
        detector.feed(_make_event("o1", "zone_b", EventType.EXIT))

        assert results == []

    def test_add_non_callable_raises(self, detector):
        with pytest.raises(TypeError):
            detector.add_callback("not_callable")  # type: ignore[arg-type]
