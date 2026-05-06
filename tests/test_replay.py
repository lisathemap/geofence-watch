"""Tests for geofence_watch.replay.EventReplayer."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.replay import EventReplayer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(ts: float, fence: str = "zone_a", obj: str = "obj1") -> GeofenceEvent:
    return GeofenceEvent(
        event_type=EventType.ENTER,
        object_id=obj,
        fence_name=fence,
        timestamp=ts,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def events() -> list[GeofenceEvent]:
    return [
        _make_event(1000.0),
        _make_event(1001.0),
        _make_event(1003.0),
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEventReplayerInit:
    def test_event_count(self, events):
        r = EventReplayer(events, callback=lambda e: None)
        assert r.event_count == 3

    def test_negative_speed_raises(self, events):
        with pytest.raises(ValueError, match="speed"):
            EventReplayer(events, callback=lambda e: None, speed=-1.0)

    def test_zero_speed_allowed(self, events):
        r = EventReplayer(events, callback=lambda e: None, speed=0)
        assert r.speed == 0


class TestEventReplayerRun:
    def test_callback_called_for_each_event(self, events):
        cb = MagicMock()
        r = EventReplayer(events, callback=cb, speed=0)
        count = r.run()
        assert count == 3
        assert cb.call_count == 3

    def test_callback_receives_correct_events(self, events):
        received: list[GeofenceEvent] = []
        r = EventReplayer(events, callback=received.append, speed=0)
        r.run()
        assert received == events

    def test_empty_events_returns_zero(self):
        cb = MagicMock()
        r = EventReplayer([], callback=cb, speed=0)
        assert r.run() == 0
        cb.assert_not_called()

    def test_stop_halts_replay(self, events):
        received: list[GeofenceEvent] = []

        def _cb(evt: GeofenceEvent) -> None:
            received.append(evt)
            replayer.stop()

        replayer = EventReplayer(events, callback=_cb, speed=0)
        replayer.run()
        assert len(received) == 1

    def test_no_delay_when_speed_zero(self, events):
        cb = MagicMock()
        r = EventReplayer(events, callback=cb, speed=0)
        start = time.monotonic()
        r.run()
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # should complete almost instantly

    def test_run_resets_stopped_flag(self, events):
        cb = MagicMock()
        r = EventReplayer(events, callback=cb, speed=0)
        r.stop()
        # After stop() is called externally, run() should reset and replay all
        count = r.run()
        assert count == 3
