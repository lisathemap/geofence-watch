"""Stream adapter that feeds GeofenceEvents through a LabelRouter."""
from __future__ import annotations

from typing import Callable, Optional

from geofence_watch.event import GeofenceEvent
from geofence_watch.label_router import LabelRouter


class RouterStream:
    """Wrap a :class:`LabelRouter` so it can sit inside a processing pipeline.

    Call :meth:`process` with a :class:`GeofenceEvent` to fan it out to all
    matching subscribers registered on the underlying router.
    """

    def __init__(self, router: Optional[LabelRouter] = None) -> None:
        self._router: LabelRouter = router if router is not None else LabelRouter()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def router(self) -> LabelRouter:
        """The underlying :class:`LabelRouter`."""
        return self._router

    # ------------------------------------------------------------------
    # Subscription helpers (thin delegation)
    # ------------------------------------------------------------------

    def subscribe(self, label: str, handler: Callable[[GeofenceEvent], None]) -> None:
        """Register *handler* under *label* on the router."""
        self._router.subscribe(label, handler)

    def unsubscribe(self, label: str, handler: Callable[[GeofenceEvent], None]) -> None:
        """Remove *handler* from *label* on the router."""
        self._router.unsubscribe(label, handler)

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self, event: GeofenceEvent) -> None:
        """Route *event* through the underlying router."""
        if not isinstance(event, GeofenceEvent):
            raise TypeError(f"Expected GeofenceEvent, got {type(event).__name__}")
        self._router.route(event)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def labels(self):
        """Labels currently active on the router."""
        return self._router.labels

    def __repr__(self) -> str:  # pragma: no cover
        return f"RouterStream(router={self._router!r})"
