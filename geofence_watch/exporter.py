"""Export geofence activity history to common formats (dict, CSV, JSON)."""

from __future__ import annotations

import csv
import io
import json
from typing import List, Dict, Any

from geofence_watch.history import ObjectHistory
from geofence_watch.event import GeofenceEvent


def _event_to_dict(event: GeofenceEvent) -> Dict[str, Any]:
    """Serialize a single GeofenceEvent to a plain dictionary."""
    return {
        "object_id": event.object_id,
        "fence_name": event.fence_name,
        "event_type": event.event_type.value,
        "latitude": event.point.lat,
        "longitude": event.point.lon,
        "timestamp": event.timestamp.isoformat() if event.timestamp is not None else None,
    }


class HistoryExporter:
    """Export an ObjectHistory to various serialisation formats."""

    def __init__(self, history: ObjectHistory) -> None:
        self._history = history

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def to_dicts(self) -> List[Dict[str, Any]]:
        """Return all recorded events as a list of plain dicts."""
        return [_event_to_dict(evt) for evt in self._history]

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialise the full history to a JSON string."""
        return json.dumps(self.to_dicts(), indent=indent)

    def to_csv(self) -> str:
        """Serialise the full history to a CSV string (headers included)."""
        fieldnames = ["object_id", "fence_name", "event_type", "latitude", "longitude", "timestamp"]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in self.to_dicts():
            writer.writerow(row)
        return buf.getvalue()

    def to_csv_file(self, path: str) -> None:
        """Write CSV output directly to *path*."""
        with open(path, "w", newline="", encoding="utf-8") as fh:
            fh.write(self.to_csv())

    def __repr__(self) -> str:  # pragma: no cover
        return f"HistoryExporter(records={len(self._history)})"
