"""Snapshot integration: periodically export history to JSON via the scheduler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from geofence_watch.exporter import HistoryExporter
from geofence_watch.history import ObjectHistory
from geofence_watch.scheduler import SnapshotScheduler


class SnapshotWriter:
    """Combines a :class:`SnapshotScheduler` with a :class:`HistoryExporter`
    to periodically write a JSON snapshot of recorded events to disk.

    Parameters
    ----------
    history:
        The :class:`ObjectHistory` instance to export.
    path:
        Destination file path for the JSON snapshot.
    interval:
        Seconds between each snapshot write.
    on_snapshot:
        Optional callback invoked after each successful write; receives the
        tick count and the path that was written.
    """

    def __init__(
        self,
        history: ObjectHistory,
        path: str | Path,
        interval: float = 60.0,
        on_snapshot: Optional[Callable[[int, Path], None]] = None,
    ) -> None:
        self._history = history
        self._path = Path(path)
        self._exporter = HistoryExporter(history)
        self._on_snapshot = on_snapshot
        self._scheduler = SnapshotScheduler(
            interval=interval,
            callback=self._write_snapshot,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start periodic snapshot writes."""
        self._scheduler.start()

    def stop(self) -> None:
        """Stop periodic snapshot writes."""
        self._scheduler.stop()

    @property
    def is_running(self) -> bool:
        return self._scheduler.is_running

    def write_now(self) -> None:
        """Immediately write a snapshot outside of the scheduled cycle."""
        self._write_snapshot(tick=0)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SnapshotWriter(path={self._path}, "
            f"interval={self._scheduler._interval}, "
            f"running={self.is_running})"
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write_snapshot(self, tick: int) -> None:
        payload = self._exporter.to_json(indent=2)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(payload, encoding="utf-8")
        if self._on_snapshot is not None:
            self._on_snapshot(tick, self._path)
