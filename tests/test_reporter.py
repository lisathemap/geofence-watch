"""Tests for ActivityReporter and FenceSummary."""
from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.history import ObjectHistory
from geofence_watch.point import Point
from geofence_watch.reporter import ActivityReporter, FenceSummary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evt(object_id: str, fence: str, etype: EventType, lon: float = 0.0, lat: float = 0.0) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence,
        event_type=etype,
        point=Point(lon, lat),
    )


@pytest.fixture()
def history() -> ObjectHistory:
    store = ObjectHistory()
    store.record(_evt("obj-1", "zone-A", EventType.ENTER))
    store.record(_evt("obj-1", "zone-A", EventType.EXIT))
    store.record(_evt("obj-1", "zone-A", EventType.ENTER))
    store.record(_evt("obj-1", "zone-B", EventType.ENTER))
    store.record(_evt("obj-2", "zone-A", EventType.ENTER))
    return store


@pytest.fixture()
def reporter(history: ObjectHistory) -> ActivityReporter:
    return ActivityReporter(history)


# ---------------------------------------------------------------------------
# FenceSummary unit tests
# ---------------------------------------------------------------------------

class TestFenceSummary:
    def test_is_inside_enter(self):
        evt = _evt("x", "z", EventType.ENTER)
        s = FenceSummary(object_id="x", fence_name="z", enter_count=1, last_event=evt)
        assert s.is_inside is True

    def test_is_inside_exit(self):
        evt = _evt("x", "z", EventType.EXIT)
        s = FenceSummary(object_id="x", fence_name="z", exit_count=1, last_event=evt)
        assert s.is_inside is False

    def test_is_inside_no_event(self):
        s = FenceSummary(object_id="x", fence_name="z")
        assert s.is_inside is False


# ---------------------------------------------------------------------------
# ActivityReporter tests
# ---------------------------------------------------------------------------

class TestActivityReporter:
    def test_summarise_counts(self, reporter: ActivityReporter):
        summaries = {s.fence_name: s for s in reporter.summarise("obj-1")}
        assert summaries["zone-A"].enter_count == 2
        assert summaries["zone-A"].exit_count == 1

    def test_summarise_last_event_is_inside(self, reporter: ActivityReporter):
        summaries = {s.fence_name: s for s in reporter.summarise("obj-1")}
        assert summaries["zone-A"].is_inside is True

    def test_summarise_multiple_fences(self, reporter: ActivityReporter):
        summaries = reporter.summarise("obj-1")
        fence_names = {s.fence_name for s in summaries}
        assert fence_names == {"zone-A", "zone-B"}

    def test_summarise_unknown_object_returns_empty(self, reporter: ActivityReporter):
        assert reporter.summarise("ghost") == []

    def test_all_summaries_keys(self, reporter: ActivityReporter):
        all_s = reporter.all_summaries()
        assert set(all_s.keys()) == {"obj-1", "obj-2"}

    def test_objects_inside(self, reporter: ActivityReporter):
        inside = reporter.objects_inside("zone-A")
        assert "obj-1" in inside
        assert "obj-2" in inside

    def test_objects_inside_excludes_exited(self):
        store = ObjectHistory()
        store.record(_evt("obj-3", "zone-C", EventType.ENTER))
        store.record(_evt("obj-3", "zone-C", EventType.EXIT))
        r = ActivityReporter(store)
        assert r.objects_inside("zone-C") == []

    def test_objects_inside_empty_fence(self, reporter: ActivityReporter):
        assert reporter.objects_inside("zone-X") == []
