"""Tests for HistoryStore and ObjectHistory, plus stream history integration."""

from __future__ import annotations

import pytest

from geofence_watch.checker import GeofenceChecker
from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.fence import Geofence
from geofence_watch.history import HistoryStore, ObjectHistory
from geofence_watch.point import Point
from geofence_watch.stream import GeofenceStream

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SQUARE_GEOJSON = {
    "type": "Feature",
    "properties": {"name": "square"},
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0], [-1.0, -1.0]]
        ],
    },
}


@pytest.fixture()
def store() -> HistoryStore:
    return HistoryStore()


@pytest.fixture()
def stream() -> GeofenceStream:
    checker = GeofenceChecker()
    checker.register(Geofence.from_geojson(SQUARE_GEOJSON))
    return GeofenceStream(checker)


def _make_event(oid: str = "obj1", fence: str = "square") -> GeofenceEvent:
    return GeofenceEvent(
        object_id=oid,
        fence_name=fence,
        event_type=EventType.ENTER,
        point=Point(lon=0.0, lat=0.0),
    )


# ---------------------------------------------------------------------------
# ObjectHistory
# ---------------------------------------------------------------------------


class TestObjectHistory:
    def test_record_and_len(self):
        h = ObjectHistory(object_id="a")
        assert len(h) == 0
        h.record(_make_event())
        assert len(h) == 1

    def test_latest_returns_last(self):
        h = ObjectHistory(object_id="a")
        e1 = _make_event()
        e2 = GeofenceEvent("a", "square", EventType.EXIT, Point(2.0, 2.0))
        h.record(e1)
        h.record(e2)
        assert h.latest() is e2

    def test_latest_empty_returns_none(self):
        assert ObjectHistory(object_id="x").latest() is None

    def test_cap_evicts_oldest(self):
        h = ObjectHistory(object_id="a", max_events=2)
        e1, e2, e3 = (_make_event() for _ in range(3))
        h.record(e1)
        h.record(e2)
        h.record(e3)
        events = list(h)
        assert len(events) == 2
        assert e1 not in events

    def test_iteration(self):
        h = ObjectHistory(object_id="a")
        evts = [_make_event() for _ in range(3)]
        for e in evts:
            h.record(e)
        assert list(h) == evts


# ---------------------------------------------------------------------------
# HistoryStore
# ---------------------------------------------------------------------------


class TestHistoryStore:
    def test_record_creates_bucket(self, store):
        store.record(_make_event(oid="car1"))
        assert "car1" in store.object_ids()

    def test_get_unknown_returns_none(self, store):
        assert store.get("ghost") is None

    def test_clear_removes_object(self, store):
        store.record(_make_event(oid="car1"))
        store.clear("car1")
        assert store.get("car1") is None

    def test_object_ids_sorted(self, store):
        for oid in ["z", "a", "m"]:
            store.record(_make_event(oid=oid))
        assert store.object_ids() == ["a", "m", "z"]

    def test_len(self, store):
        store.record(_make_event(oid="a"))
        store.record(_make_event(oid="b"))
        assert len(store) == 2


# ---------------------------------------------------------------------------
# Stream ↔ History integration
# ---------------------------------------------------------------------------


class TestStreamHistory:
    def test_enter_recorded(self, stream):
        stream.process("drone", Point(0.5, 0.5))  # seed
        stream.process("drone", Point(2.0, 2.0))  # exit — seeds first
        # Re-enter
        stream.process("drone", Point(0.0, 0.0))
        history = stream.history.get("drone")
        assert history is not None
        latest = history.latest()
        assert latest.event_type == EventType.ENTER

    def test_reset_clears_history(self, stream):
        stream.process("drone", Point(0.5, 0.5))
        stream.process("drone", Point(2.0, 2.0))
        stream.reset("drone")
        assert stream.history.get("drone") is None

    def test_max_history_respected(self):
        checker = GeofenceChecker()
        checker.register(Geofence.from_geojson(SQUARE_GEOJSON))
        s = GeofenceStream(checker, max_history=2)
        # Alternate in/out to generate events
        pts = [Point(0, 0), Point(2, 2), Point(0, 0), Point(2, 2), Point(0, 0)]
        list(s.process_many("x", pts))
        hist = s.history.get("x")
        assert hist is not None
        assert len(hist) <= 2
