"""Tests for DwellStream."""

from __future__ import annotations

import time
from typing import List

import pytest

from geofence_watch.dwell_stream import DwellStream
from geofence_watch.dwell_tracker import DwellRecord, DwellTracker
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(event_type: EventType, obj_id: str = "obj1", fence: str = "zone_a") -> GeofenceEvent:
    return GeofenceEvent(
        event_type=event_type,
        object_id=obj_id,
        fence_name=fence,
        point=Point(0.0, 0.0),
        timestamp=time.time(),
    )


@pytest.fixture()
def stream() -> DwellStream:
    return DwellStream()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestDwellStreamInit:
    def test_default_tracker_created(self, stream: DwellStream) -> None:
        assert isinstance(stream.tracker, DwellTracker)

    def test_custom_tracker_accepted(self) -> None:
        t = DwellTracker()
        s = DwellStream(tracker=t)
        assert s.tracker is t

    def test_invalid_tracker_raises(self) -> None:
        with pytest.raises(TypeError):
            DwellStream(tracker="bad")  # type: ignore[arg-type]

    def test_no_callbacks_initially(self, stream: DwellStream) -> None:
        assert stream.callback_names == []


# ---------------------------------------------------------------------------
# Callback management
# ---------------------------------------------------------------------------

class TestDwellStreamCallbacks:
    def test_add_callback(self, stream: DwellStream) -> None:
        stream.add_callback("cb", lambda r: None)
        assert "cb" in stream.callback_names

    def test_duplicate_callback_raises(self, stream: DwellStream) -> None:
        stream.add_callback("cb", lambda r: None)
        with pytest.raises(ValueError):
            stream.add_callback("cb", lambda r: None)

    def test_non_callable_raises(self, stream: DwellStream) -> None:
        with pytest.raises(TypeError):
            stream.add_callback("cb", "not_callable")  # type: ignore[arg-type]

    def test_remove_callback(self, stream: DwellStream) -> None:
        stream.add_callback("cb", lambda r: None)
        stream.remove_callback("cb")
        assert "cb" not in stream.callback_names

    def test_remove_missing_raises(self, stream: DwellStream) -> None:
        with pytest.raises(KeyError):
            stream.remove_callback("ghost")


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

class TestDwellStreamProcess:
    def test_enter_returns_record(self, stream: DwellStream) -> None:
        evt = _make_event(EventType.ENTER)
        record = stream.process(evt)
        assert isinstance(record, DwellRecord)

    def test_inside_returns_none(self, stream: DwellStream) -> None:
        stream.process(_make_event(EventType.ENTER))
        record = stream.process(_make_event(EventType.INSIDE))
        assert record is None

    def test_callback_invoked_on_enter(self, stream: DwellStream) -> None:
        received: List[DwellRecord] = []
        stream.add_callback("sink", received.append)
        stream.process(_make_event(EventType.ENTER))
        assert len(received) == 1
        assert received[0].object_id == "obj1"

    def test_callback_not_invoked_on_inside(self, stream: DwellStream) -> None:
        received: List[DwellRecord] = []
        stream.add_callback("sink", received.append)
        stream.process(_make_event(EventType.ENTER))
        received.clear()
        stream.process(_make_event(EventType.INSIDE))
        assert received == []

    def test_multiple_callbacks_all_invoked(self, stream: DwellStream) -> None:
        counts: List[int] = [0, 0]
        stream.add_callback("a", lambda r: counts.__setitem__(0, counts[0] + 1))
        stream.add_callback("b", lambda r: counts.__setitem__(1, counts[1] + 1))
        stream.process(_make_event(EventType.ENTER))
        assert counts == [1, 1]
