"""Tests for LabelRouter and RouterStream."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.point import Point
from geofence_watch.label_router import LabelRouter
from geofence_watch.router_stream import RouterStream


def _make_event(
    fence: str = "zone_a",
    etype: EventType = EventType.ENTER,
    obj: str = "obj1",
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=obj,
        fence_name=fence,
        event_type=etype,
        point=Point(lon=1.0, lat=2.0),
        timestamp=0.0,
    )


# ---------------------------------------------------------------------------
# LabelRouter
# ---------------------------------------------------------------------------

class TestLabelRouterSubscribe:
    def test_subscribe_callable_ok(self):
        router = LabelRouter()
        router.subscribe("zone_a", lambda e: None)
        assert "zone_a" in router.labels

    def test_subscribe_non_callable_raises(self):
        router = LabelRouter()
        with pytest.raises(TypeError):
            router.subscribe("zone_a", "not_callable")

    def test_subscribe_empty_label_raises(self):
        router = LabelRouter()
        with pytest.raises(ValueError):
            router.subscribe("", lambda e: None)

    def test_subscriber_count(self):
        router = LabelRouter()
        h1, h2 = MagicMock(), MagicMock()
        router.subscribe("zone_a", h1)
        router.subscribe("zone_a", h2)
        assert router.subscriber_count("zone_a") == 2

    def test_unsubscribe_removes_handler(self):
        router = LabelRouter()
        h = MagicMock()
        router.subscribe("zone_a", h)
        router.unsubscribe("zone_a", h)
        assert router.subscriber_count("zone_a") == 0

    def test_unsubscribe_unknown_is_silent(self):
        router = LabelRouter()
        router.unsubscribe("nope", lambda e: None)  # should not raise


class TestLabelRouterRoute:
    def test_fence_name_handler_called(self):
        router = LabelRouter()
        h = MagicMock()
        router.subscribe("zone_a", h)
        evt = _make_event(fence="zone_a")
        router.route(evt)
        h.assert_called_once_with(evt)

    def test_event_type_handler_called(self):
        router = LabelRouter()
        h = MagicMock()
        router.subscribe("ENTER", h)
        evt = _make_event(etype=EventType.ENTER)
        router.route(evt)
        h.assert_called_once_with(evt)

    def test_wildcard_receives_every_event(self):
        router = LabelRouter()
        h = MagicMock()
        router.subscribe("*", h)
        router.route(_make_event(fence="zone_a"))
        router.route(_make_event(fence="zone_b", etype=EventType.EXIT))
        assert h.call_count == 2

    def test_handler_called_once_even_if_multiple_labels_match(self):
        """A handler registered under both fence name and '*' must fire once."""
        router = LabelRouter()
        h = MagicMock()
        router.subscribe("zone_a", h)
        router.subscribe("*", h)
        router.route(_make_event(fence="zone_a"))
        # h appears under two matching labels but should be deduplicated
        assert h.call_count == 1

    def test_non_matching_handler_not_called(self):
        router = LabelRouter()
        h = MagicMock()
        router.subscribe("zone_b", h)
        router.route(_make_event(fence="zone_a"))
        h.assert_not_called()


# ---------------------------------------------------------------------------
# RouterStream
# ---------------------------------------------------------------------------

@pytest.fixture()
def stream():
    return RouterStream()


def test_default_router_created(stream):
    assert isinstance(stream.router, LabelRouter)


def test_custom_router_accepted():
    r = LabelRouter()
    rs = RouterStream(router=r)
    assert rs.router is r


def test_process_routes_event(stream):
    h = MagicMock()
    stream.subscribe("zone_a", h)
    evt = _make_event(fence="zone_a")
    stream.process(evt)
    h.assert_called_once_with(evt)


def test_process_wrong_type_raises(stream):
    with pytest.raises(TypeError):
        stream.process("not_an_event")


def test_labels_delegated(stream):
    stream.subscribe("zone_x", MagicMock())
    assert "zone_x" in stream.labels
