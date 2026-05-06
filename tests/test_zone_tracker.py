"""Tests for ZoneTracker and ZoneStream."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.zone_tracker import ZoneTracker
from geofence_watch.zone_stream import ZoneStream


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evt(object_id: str, fence: str, etype: EventType) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence,
        event_type=etype,
        point=Point(lon=0.0, lat=0.0),
    )


# ---------------------------------------------------------------------------
# ZoneTracker
# ---------------------------------------------------------------------------

class TestZoneTracker:
    def test_initial_state_empty(self):
        zt = ZoneTracker()
        assert len(zt) == 0
        assert zt.tracked_objects == set()

    def test_enter_adds_fence(self):
        zt = ZoneTracker()
        zt.ingest(_evt("car1", "zone_a", EventType.ENTER))
        assert zt.is_inside("car1", "zone_a")

    def test_exit_removes_fence(self):
        zt = ZoneTracker()
        zt.ingest(_evt("car1", "zone_a", EventType.ENTER))
        zt.ingest(_evt("car1", "zone_a", EventType.EXIT))
        assert not zt.is_inside("car1", "zone_a")

    def test_zones_for_multiple_fences(self):
        zt = ZoneTracker()
        zt.ingest(_evt("car1", "zone_a", EventType.ENTER))
        zt.ingest(_evt("car1", "zone_b", EventType.ENTER))
        assert zt.zones_for("car1") == {"zone_a", "zone_b"}

    def test_objects_in_fence(self):
        zt = ZoneTracker()
        zt.ingest(_evt("car1", "zone_a", EventType.ENTER))
        zt.ingest(_evt("car2", "zone_a", EventType.ENTER))
        zt.ingest(_evt("car3", "zone_b", EventType.ENTER))
        assert zt.objects_in("zone_a") == {"car1", "car2"}

    def test_unknown_object_returns_empty_zones(self):
        zt = ZoneTracker()
        assert zt.zones_for("ghost") == set()

    def test_is_inside_false_for_unknown(self):
        zt = ZoneTracker()
        assert not zt.is_inside("ghost", "zone_a")

    def test_remove_object(self):
        zt = ZoneTracker()
        zt.ingest(_evt("car1", "zone_a", EventType.ENTER))
        zt.remove_object("car1")
        assert "car1" not in zt.tracked_objects

    def test_clear_resets_all(self):
        zt = ZoneTracker()
        zt.ingest(_evt("car1", "zone_a", EventType.ENTER))
        zt.ingest(_evt("car2", "zone_b", EventType.ENTER))
        zt.clear()
        assert len(zt) == 0

    def test_exit_on_unknown_object_is_safe(self):
        zt = ZoneTracker()
        # Should not raise
        zt.ingest(_evt("car1", "zone_a", EventType.EXIT))
        assert not zt.is_inside("car1", "zone_a")


# ---------------------------------------------------------------------------
# ZoneStream
# ---------------------------------------------------------------------------

class TestZoneStream:
    def _make_zone_stream(self):
        mock_stream = MagicMock()
        captured = []
        mock_stream.add_callback.side_effect = lambda cb: captured.append(cb)
        zs = ZoneStream(mock_stream)
        return zs, captured

    def test_tracker_property_returns_zone_tracker(self):
        zs, _ = self._make_zone_stream()
        assert isinstance(zs.tracker, ZoneTracker)

    def test_event_updates_tracker(self):
        zs, captured = self._make_zone_stream()
        on_event = captured[0]
        on_event(_evt("car1", "zone_a", EventType.ENTER))
        assert zs.is_inside("car1", "zone_a")

    def test_callback_called_after_tracker_update(self):
        zs, captured = self._make_zone_stream()
        on_event = captured[0]
        received = []
        zs.add_callback(received.append)
        on_event(_evt("car1", "zone_a", EventType.ENTER))
        assert len(received) == 1
        assert zs.is_inside("car1", "zone_a")

    def test_add_non_callable_raises(self):
        zs, _ = self._make_zone_stream()
        with pytest.raises(TypeError):
            zs.add_callback("not_a_function")  # type: ignore

    def test_remove_callback(self):
        zs, captured = self._make_zone_stream()
        on_event = captured[0]
        received = []
        zs.add_callback(received.append)
        zs.remove_callback(received.append)
        on_event(_evt("car1", "zone_a", EventType.ENTER))
        assert len(received) == 0

    def test_callback_count(self):
        zs, _ = self._make_zone_stream()
        assert zs.callback_count == 0
        zs.add_callback(lambda e: None)
        assert zs.callback_count == 1
