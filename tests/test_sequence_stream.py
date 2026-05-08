"""Tests for SequenceStream."""
from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.sequence_detector import SequenceDetector, SequenceMatch
from geofence_watch.sequence_stream import SequenceStream


def _make_event(
    object_id: str,
    fence_name: str,
    event_type: EventType,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(1.0, 1.0),
    )


PATTERN = [
    ("alpha", EventType.ENTER),
    ("beta", EventType.EXIT),
]


@pytest.fixture()
def stream() -> SequenceStream:
    return SequenceStream(PATTERN)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestSequenceStreamInit:
    def test_detector_created(self, stream):
        assert isinstance(stream.detector, SequenceDetector)

    def test_custom_detector_accepted(self):
        det = SequenceDetector(PATTERN)
        s = SequenceStream(PATTERN, detector=det)
        assert s.detector is det

    def test_invalid_detector_raises(self):
        with pytest.raises(TypeError):
            SequenceStream(PATTERN, detector="bad")  # type: ignore[arg-type]

    def test_no_callbacks_initially(self, stream):
        assert stream.callback_names() == []


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

class TestSequenceStreamDelegation:
    def test_process_triggers_callback(self, stream):
        results = []
        stream.add_callback(results.append)

        stream.process(_make_event("obj", "alpha", EventType.ENTER))
        stream.process(_make_event("obj", "beta", EventType.EXIT))

        assert len(results) == 1
        assert isinstance(results[0], SequenceMatch)

    def test_progress_delegated(self, stream):
        stream.process(_make_event("obj", "alpha", EventType.ENTER))
        assert stream.progress("obj") == 1

    def test_reset_delegated(self, stream):
        stream.process(_make_event("obj", "alpha", EventType.ENTER))
        stream.reset("obj")
        assert stream.progress("obj") == 0

    def test_remove_callback(self, stream):
        results = []
        stream.add_callback(results.append)
        stream.remove_callback(results.append)

        stream.process(_make_event("obj", "alpha", EventType.ENTER))
        stream.process(_make_event("obj", "beta", EventType.EXIT))

        assert results == []

    def test_callback_names_populated(self, stream):
        def my_handler(m: SequenceMatch) -> None:
            pass

        stream.add_callback(my_handler)
        assert "my_handler" in stream.callback_names()
