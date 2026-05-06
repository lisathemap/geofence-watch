"""Tests for geofence_watch.transformer.EventTransformer."""

from __future__ import annotations

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.transformer import EventTransformer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    object_id: str = "obj-1",
    fence_name: str = "zone-a",
    event_type: EventType = EventType.ENTER,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(lon=10.0, lat=20.0),
    )


# ---------------------------------------------------------------------------
# Init / registration
# ---------------------------------------------------------------------------

class TestEventTransformerInit:
    def test_starts_empty(self):
        t = EventTransformer()
        assert t.transform_count == 0

    def test_add_increments_count(self):
        t = EventTransformer()
        t.add(lambda e: {})
        assert t.transform_count == 1

    def test_add_non_callable_raises(self):
        t = EventTransformer()
        with pytest.raises(TypeError, match="callable"):
            t.add("not_a_function")  # type: ignore[arg-type]

    def test_clear_resets_count(self):
        t = EventTransformer()
        t.add(lambda e: {})
        t.add(lambda e: {})
        t.clear()
        assert t.transform_count == 0


# ---------------------------------------------------------------------------
# apply()
# ---------------------------------------------------------------------------

class TestApply:
    def test_no_transforms_returns_none(self):
        t = EventTransformer()
        assert t.apply(_make_event()) is None

    def test_single_transform_returns_dict(self):
        t = EventTransformer()
        t.add(lambda e: {"id": e.object_id})
        result = t.apply(_make_event(object_id="car-7"))
        assert result == {"id": "car-7"}

    def test_transform_returning_none_drops_event(self):
        t = EventTransformer()
        t.add(lambda e: {"id": e.object_id})
        t.add(lambda e: None)  # drop everything
        assert t.apply(_make_event()) is None

    def test_last_transform_result_wins(self):
        t = EventTransformer()
        t.add(lambda e: {"step": 1})
        t.add(lambda e: {"step": 2})
        result = t.apply(_make_event())
        assert result == {"step": 2}

    def test_conditional_drop_by_event_type(self):
        t = EventTransformer()
        t.add(
            lambda e: None
            if e.event_type == EventType.EXIT
            else {"id": e.object_id}
        )
        assert t.apply(_make_event(event_type=EventType.ENTER)) == {"id": "obj-1"}
        assert t.apply(_make_event(event_type=EventType.EXIT)) is None


# ---------------------------------------------------------------------------
# run_all()
# ---------------------------------------------------------------------------

class TestRunAll:
    def test_empty_list(self):
        t = EventTransformer()
        t.add(lambda e: {"id": e.object_id})
        assert t.run_all([]) == []

    def test_all_pass_through(self):
        t = EventTransformer()
        t.add(lambda e: {"id": e.object_id})
        events = [_make_event(object_id=f"obj-{i}") for i in range(3)]
        results = t.run_all(events)
        assert len(results) == 3
        assert [r["id"] for r in results] == ["obj-0", "obj-1", "obj-2"]

    def test_dropped_events_excluded(self):
        t = EventTransformer()
        t.add(
            lambda e: None
            if e.fence_name == "skip-zone"
            else {"fence": e.fence_name}
        )
        events = [
            _make_event(fence_name="zone-a"),
            _make_event(fence_name="skip-zone"),
            _make_event(fence_name="zone-b"),
        ]
        results = t.run_all(events)
        assert len(results) == 2
        assert results[0]["fence"] == "zone-a"
        assert results[1]["fence"] == "zone-b"
