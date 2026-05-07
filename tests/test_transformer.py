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

    def test_transform_receives_correct_fence_name(self):
        """Verify that the full GeofenceEvent is passed to each transform."""
        t = EventTransformer()
        t.add(lambda e: {"fence": e.fence_name})
        result = t.apply(_make_event(fence_name="restricted-zone"))
        assert result == {"fence": "restricted-zone"}

    def test_apply_after_clear_returns_none(self):
        """Clearing transforms should cause apply() to return None again."""
        t = EventTransformer()
        t.add(lambda e: {"id": e.object_id})
        assert t.apply(_make_event()) is not None
        t.clear()
        assert t.apply(_make_event()) is None


# -------------------------------------------------------
