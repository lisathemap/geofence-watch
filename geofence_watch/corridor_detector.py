"""Corridor detector: checks whether an object's path stays within
a sequence of ordered geofences (a 'corridor')."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .event import EventType, GeofenceEvent


@dataclass
class CorridorResult:
    """Outcome of a corridor evaluation for one object."""

    object_id: str
    corridor_name: str
    current_step: int          # 0-based index of the last matched fence
    total_steps: int
    completed: bool            # True when all steps have been visited in order
    deviated: bool             # True when an unexpected fence was entered

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"CorridorResult(object={self.object_id!r}, corridor={self.corridor_name!r}, "
            f"step={self.current_step}/{self.total_steps}, "
            f"completed={self.completed}, deviated={self.deviated})"
        )


class CorridorDetector:
    """Tracks per-object progress through an ordered sequence of geofences.

    Parameters
    ----------
    name:
        Human-readable label for this corridor.
    steps:
        Ordered list of fence names that form the corridor.
    strict:
        When *True*, entering a fence that is not the next expected step
        marks the object as deviated and resets its progress.
    """

    def __init__(
        self,
        name: str,
        steps: Sequence[str],
        *,
        strict: bool = True,
    ) -> None:
        if not name:
            raise ValueError("corridor name must be non-empty")
        if len(steps) < 2:
            raise ValueError("a corridor requires at least 2 steps")
        self._name: str = name
        self._steps: Tuple[str, ...] = tuple(steps)
        self._strict: bool = strict
        # object_id -> current step index
        self._progress: Dict[str, int] = {}
        self._deviated: Dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def steps(self) -> Tuple[str, ...]:
        return self._steps

    @property
    def strict(self) -> bool:
        return self._strict

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------

    def ingest(self, event: GeofenceEvent) -> Optional[CorridorResult]:
        """Process one geofence event and return a result if progress changed."""
        if event.event_type != EventType.ENTER:
            return None

        oid = event.object_id
        fence = event.fence_name

        step = self._progress.get(oid, 0)
        deviated = self._deviated.get(oid, False)

        if fence == self._steps[step]:
            step += 1
            self._progress[oid] = step
            completed = step == len(self._steps)
            result = CorridorResult(
                object_id=oid,
                corridor_name=self._name,
                current_step=step,
                total_steps=len(self._steps),
                completed=completed,
                deviated=False,
            )
            if completed:
                self.reset(oid)
            return result

        if self._strict and fence in self._steps:
            self._deviated[oid] = True
            self._progress[oid] = 0
            return CorridorResult(
                object_id=oid,
                corridor_name=self._name,
                current_step=0,
                total_steps=len(self._steps),
                completed=False,
                deviated=True,
            )

        return None

    def reset(self, object_id: str) -> None:
        """Clear progress for *object_id*."""
        self._progress.pop(object_id, None)
        self._deviated.pop(object_id, None)

    def progress(self, object_id: str) -> int:
        """Return the current 0-based step index for *object_id*."""
        return self._progress.get(object_id, 0)
