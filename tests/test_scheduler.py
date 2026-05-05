"""Tests for SnapshotScheduler and SnapshotWriter."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.history import ObjectHistory
from geofence_watch.point import Point
from geofence_watch.scheduler import SnapshotScheduler
from geofence_watch.snapshot import SnapshotWriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(obj_id: str = "obj-1", fence: str = "zone-a") -> GeofenceEvent:
    return GeofenceEvent(
        object_id=obj_id,
        fence_name=fence,
        event_type=EventType.ENTER,
        point=Point(lon=1.0, lat=2.0),
        timestamp=0.0,
    )


# ---------------------------------------------------------------------------
# SnapshotScheduler
# ---------------------------------------------------------------------------

class TestSnapshotScheduler:
    def test_invalid_interval_raises(self):
        with pytest.raises(ValueError):
            SnapshotScheduler(interval=0, callback=lambda t: None)

    def test_negative_interval_raises(self):
        with pytest.raises(ValueError):
            SnapshotScheduler(interval=-1, callback=lambda t: None)

    def test_callback_is_called(self):
        ticks = []
        sched = SnapshotScheduler(interval=0.05, callback=lambda t: ticks.append(t))
        sched.start()
        time.sleep(0.18)
        sched.stop()
        assert len(ticks) >= 2
        assert ticks[0] == 1

    def test_is_running_reflects_state(self):
        sched = SnapshotScheduler(interval=0.1, callback=lambda t: None)
        assert not sched.is_running
        sched.start()
        assert sched.is_running
        sched.stop()
        assert not sched.is_running

    def test_double_start_raises(self):
        sched = SnapshotScheduler(interval=0.1, callback=lambda t: None)
        sched.start()
        try:
            with pytest.raises(RuntimeError):
                sched.start()
        finally:
            sched.stop()

    def test_tick_count_increments(self):
        sched = SnapshotScheduler(interval=0.05, callback=lambda t: None)
        sched.start()
        time.sleep(0.22)
        sched.stop()
        assert sched.tick >= 3

    def test_callback_exception_does_not_stop_scheduler(self):
        calls = []

        def bad_callback(t):
            calls.append(t)
            raise RuntimeError("boom")

        sched = SnapshotScheduler(interval=0.05, callback=bad_callback)
        sched.start()
        time.sleep(0.18)
        sched.stop()
        assert len(calls) >= 2


# ---------------------------------------------------------------------------
# SnapshotWriter
# ---------------------------------------------------------------------------

class TestSnapshotWriter:
    def test_write_now_creates_file(self, tmp_path):
        hist = ObjectHistory()
        hist.record(_make_event())
        out = tmp_path / "snap.json"
        writer = SnapshotWriter(history=hist, path=out, interval=60.0)
        writer.write_now()
        assert out.exists()
        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert len(data) == 1

    def test_on_snapshot_callback_called(self, tmp_path):
        hist = ObjectHistory()
        hist.record(_make_event())
        cb = MagicMock()
        out = tmp_path / "snap.json"
        writer = SnapshotWriter(history=hist, path=out, interval=60.0, on_snapshot=cb)
        writer.write_now()
        cb.assert_called_once_with(0, out)

    def test_scheduled_write(self, tmp_path):
        hist = ObjectHistory()
        hist.record(_make_event())
        out = tmp_path / "auto.json"
        writer = SnapshotWriter(history=hist, path=out, interval=0.06)
        writer.start()
        time.sleep(0.2)
        writer.stop()
        assert out.exists()

    def test_creates_parent_dirs(self, tmp_path):
        hist = ObjectHistory()
        out = tmp_path / "nested" / "deep" / "snap.json"
        writer = SnapshotWriter(history=hist, path=out, interval=60.0)
        writer.write_now()
        assert out.exists()
