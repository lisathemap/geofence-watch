"""Tests for VisitCounter and VisitStream."""

from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.visit_counter import VisitCounter
from geofence_watch.visit_stream import VisitStream


def _make_event(etype: EventType, obj: str = "obj1", fence: str = "zone_a") -> GeofenceEvent:
    return GeofenceEvent(
        event_type=etype,
        object_id=obj,
        fence_name=fence,
        point=Point(lon=0.0, lat=0.0),
        timestamp=0.0,
    )


# ---------------------------------------------------------------------------
# VisitCounter – init
# ---------------------------------------------------------------------------

class TestVisitCounterInit:
    def test_default_track_objects_is_none(self):
        vc = VisitCounter()
        assert vc.track_objects is None

    def test_custom_track_objects_stored_as_tuple(self):
        vc = VisitCounter(track_objects=["a", "b"])
        assert vc.track_objects == ("a", "b")

    def test_count_unknown_pair_is_zero(self):
        vc = VisitCounter()
        assert vc.count("x", "y") == 0


# ---------------------------------------------------------------------------
# VisitCounter – ingest
# ---------------------------------------------------------------------------

class TestVisitCounterIngest:
    def test_enter_increments_count(self):
        vc = VisitCounter()
        vc.ingest(_make_event(EventType.ENTER))
        assert vc.count("obj1", "zone_a") == 1

    def test_exit_does_not_increment(self):
        vc = VisitCounter()
        vc.ingest(_make_event(EventType.EXIT))
        assert vc.count("obj1", "zone_a") == 0

    def test_multiple_enters_accumulate(self):
        vc = VisitCounter()
        for _ in range(3):
            vc.ingest(_make_event(EventType.ENTER))
        assert vc.count("obj1", "zone_a") == 3

    def test_filtered_object_ignored(self):
        vc = VisitCounter(track_objects=["obj2"])
        vc.ingest(_make_event(EventType.ENTER, obj="obj1"))
        assert vc.count("obj1", "zone_a") == 0

    def test_tracked_object_counted(self):
        vc = VisitCounter(track_objects=["obj1"])
        vc.ingest(_make_event(EventType.ENTER, obj="obj1"))
        assert vc.count("obj1", "zone_a") == 1

    def test_total_for_object(self):
        vc = VisitCounter()
        vc.ingest(_make_event(EventType.ENTER, fence="zone_a"))
        vc.ingest(_make_event(EventType.ENTER, fence="zone_b"))
        assert vc.total_for_object("obj1") == 2

    def test_total_for_fence(self):
        vc = VisitCounter()
        vc.ingest(_make_event(EventType.ENTER, obj="obj1"))
        vc.ingest(_make_event(EventType.ENTER, obj="obj2"))
        assert vc.total_for_fence("zone_a") == 2

    def test_snapshot_is_copy(self):
        vc = VisitCounter()
        vc.ingest(_make_event(EventType.ENTER))
        snap = vc.snapshot()
        snap[("obj1", "zone_a")] = 99
        assert vc.count("obj1", "zone_a") == 1


# ---------------------------------------------------------------------------
# VisitCounter – reset
# ---------------------------------------------------------------------------

class TestVisitCounterReset:
    def test_reset_all(self):
        vc = VisitCounter()
        vc.ingest(_make_event(EventType.ENTER))
        vc.reset()
        assert vc.count("obj1", "zone_a") == 0

    def test_reset_by_object(self):
        vc = VisitCounter()
        vc.ingest(_make_event(EventType.ENTER, obj="obj1"))
        vc.ingest(_make_event(EventType.ENTER, obj="obj2"))
        vc.reset(object_id="obj1")
        assert vc.count("obj1", "zone_a") == 0
        assert vc.count("obj2", "zone_a") == 1

    def test_reset_by_fence(self):
        vc = VisitCounter()
        vc.ingest(_make_event(EventType.ENTER, fence="zone_a"))
        vc.ingest(_make_event(EventType.ENTER, fence="zone_b"))
        vc.reset(fence_name="zone_a")
        assert vc.count("obj1", "zone_a") == 0
        assert vc.count("obj1", "zone_b") == 1


# ---------------------------------------------------------------------------
# VisitStream
# ---------------------------------------------------------------------------

@pytest.fixture()
def stream() -> VisitStream:
    return VisitStream()


class TestVisitStreamInit:
    def test_default_counter_created(self, stream):
        assert isinstance(stream.counter, VisitCounter)

    def test_custom_counter_accepted(self):
        vc = VisitCounter(track_objects=["x"])
        vs = VisitStream(counter=vc)
        assert vs.counter is vc

    def test_no_callbacks_initially(self, stream):
        assert stream.callback_names == ()


class TestVisitStreamCallbacks:
    def test_add_callback(self, stream):
        stream.add_callback("cb", lambda e, c: None)
        assert "cb" in stream.callback_names

    def test_remove_callback(self, stream):
        stream.add_callback("cb", lambda e, c: None)
        stream.remove_callback("cb")
        assert "cb" not in stream.callback_names

    def test_non_callable_raises(self, stream):
        with pytest.raises(TypeError):
            stream.add_callback("bad", "not_callable")  # type: ignore

    def test_empty_name_raises(self, stream):
        with pytest.raises(ValueError):
            stream.add_callback("", lambda e, c: None)

    def test_callback_fired_on_enter(self, stream):
        received = []
        stream.add_callback("cb", lambda e, c: received.append((e, c)))
        evt = _make_event(EventType.ENTER)
        stream.process(evt)
        assert len(received) == 1
        assert received[0][0] is evt

    def test_callback_not_fired_on_exit(self, stream):
        received = []
        stream.add_callback("cb", lambda e, c: received.append(e))
        stream.process(_make_event(EventType.EXIT))
        assert received == []

    def test_counter_updated_before_callback(self, stream):
        counts_at_callback = []
        stream.add_callback(
            "cb",
            lambda e, c: counts_at_callback.append(c.count(e.object_id, e.fence_name)),
        )
        stream.process(_make_event(EventType.ENTER))
        assert counts_at_callback == [1]
