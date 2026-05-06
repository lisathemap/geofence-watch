"""Replay recorded GeofenceEvents through a callback at controlled speed."""

from __future__ import annotations

import time
from typing import Callable, Iterable, Optional

from geofence_watch.event import GeofenceEvent


class EventReplayer:
    """Replay a sequence of GeofenceEvents with optional time scaling.

    Parameters
    ----------
    events:
        Ordered iterable of GeofenceEvent objects to replay.
    callback:
        Callable invoked with each event as it is replayed.
    speed:
        Playback multiplier.  ``1.0`` replays at real-time gaps;
        ``2.0`` replays at double speed; ``0`` replays with no delay.
    """

    def __init__(
        self,
        events: Iterable[GeofenceEvent],
        callback: Callable[[GeofenceEvent], None],
        speed: float = 1.0,
    ) -> None:
        if speed < 0:
            raise ValueError(f"speed must be >= 0, got {speed}")
        self._events: list[GeofenceEvent] = list(events)
        self._callback = callback
        self.speed = speed
        self._stopped = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def event_count(self) -> int:
        """Total number of events queued for replay."""
        return len(self._events)

    def stop(self) -> None:
        """Signal the replayer to stop after the current event."""
        self._stopped = True

    def run(self) -> int:
        """Replay all events sequentially.  Returns number of events emitted."""
        self._stopped = False
        emitted = 0
        prev_ts: Optional[float] = None

        for event in self._events:
            if self._stopped:
                break

            if prev_ts is not None and self.speed > 0:
                gap = event.timestamp - prev_ts
                delay = gap / self.speed
                if delay > 0:
                    time.sleep(delay)

            self._callback(event)
            prev_ts = event.timestamp
            emitted += 1

        return emitted

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"EventReplayer(events={self.event_count}, speed={self.speed})"
        )
