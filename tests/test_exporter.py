"""Tests for geofence_watch.exporter.HistoryExporter."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone

import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.exporter import HistoryExporter, _event_to_dict
from geofence_watch.history import ObjectHistory
from geofence_watch.point import Point


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_event(
    object_id: str = "obj-1",
    fence_name: str = "zone-a",
    event_type: EventType = EventType.ENTER,
    lon: float = 10.0,
    lat: float = 50.0,
    timestamp: datetime | None = TS,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=object_id,
        fence_name=fence_name,
        event_type=event_type,
        point=Point(lon=lon, lat=lat),
        timestamp=timestamp,
    )


@pytest.fixture()
def history() -> ObjectHistory:
    store = ObjectHistory(max_per_object=50)
    store.record(_make_event(event_type=EventType.ENTER))
    store.record(_make_event(event_type=EventType.EXIT))
    return store


@pytest.fixture()
def exporter(history: ObjectHistory) -> HistoryExporter:
    return HistoryExporter(history)


# ---------------------------------------------------------------------------
# _event_to_dict
# ---------------------------------------------------------------------------

class TestEventToDict:
    def test_keys_present(self):
        d = _event_to_dict(_make_event())
        assert set(d.keys()) == {"object_id", "fence_name", "event_type", "latitude", "longitude", "timestamp"}

    def test_values(self):
        d = _event_to_dict(_make_event())
        assert d["object_id"] == "obj-1"
        assert d["fence_name"] == "zone-a"
        assert d["event_type"] == EventType.ENTER.value
        assert d["latitude"] == 50.0
        assert d["longitude"] == 10.0
        assert d["timestamp"] == TS.isoformat()

    def test_none_timestamp(self):
        d = _event_to_dict(_make_event(timestamp=None))
        assert d["timestamp"] is None


# ---------------------------------------------------------------------------
# HistoryExporter
# ---------------------------------------------------------------------------

class TestHistoryExporter:
    def test_to_dicts_length(self, exporter: HistoryExporter):
        assert len(exporter.to_dicts()) == 2

    def test_to_dicts_event_types(self, exporter: HistoryExporter):
        types = [d["event_type"] for d in exporter.to_dicts()]
        assert EventType.ENTER.value in types
        assert EventType.EXIT.value in types

    def test_to_json_is_valid(self, exporter: HistoryExporter):
        raw = exporter.to_json()
        parsed = json.loads(raw)
        assert isinstance(parsed, list)
        assert len(parsed) == 2

    def test_to_json_no_indent(self, exporter: HistoryExporter):
        raw = exporter.to_json(indent=None)
        assert "\n" not in raw

    def test_to_csv_has_header(self, exporter: HistoryExporter):
        raw = exporter.to_csv()
        reader = csv.DictReader(io.StringIO(raw))
        assert "event_type" in reader.fieldnames

    def test_to_csv_row_count(self, exporter: HistoryExporter):
        raw = exporter.to_csv()
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
        assert len(rows) == 2

    def test_to_csv_file(self, exporter: HistoryExporter, tmp_path):
        path = str(tmp_path / "export.csv")
        exporter.to_csv_file(path)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert "event_type" in content
        assert EventType.ENTER.value in content

    def test_empty_history(self):
        empty = ObjectHistory()
        exp = HistoryExporter(empty)
        assert exp.to_dicts() == []
        assert json.loads(exp.to_json()) == []
        rows = list(csv.DictReader(io.StringIO(exp.to_csv())))
        assert rows == []
