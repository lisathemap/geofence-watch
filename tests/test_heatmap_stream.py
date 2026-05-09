"""Tests for HeatmapStream."""
import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.heatmap import HeatmapBuilder
from geofence_watch.heatmap_stream import HeatmapStream
from geofence_watch.point import Point


def _make_event(obj: str, fence: str, etype: EventType) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=obj,
        fence_name=fence,
        event_type=etype,
        point=Point(0.0, 0.0),
    )


@pytest.fixture()
def stream() -> HeatmapStream:
    return HeatmapStream()


class TestHeatmapStreamInit:
    def test_default_builder_created(self, stream: HeatmapStream) -> None:
        assert isinstance(stream.builder, HeatmapBuilder)

    def test_custom_builder_accepted(self) -> None:
        b = HeatmapBuilder()
        s = HeatmapStream(builder=b)
        assert s.builder is b

    def test_invalid_builder_raises(self) -> None:
        with pytest.raises(TypeError):
            HeatmapStream(builder="bad")  # type: ignore[arg-type]

    def test_no_callbacks_initially(self, stream: HeatmapStream) -> None:
        assert stream.callback_names == []


class TestCallbackManagement:
    def test_add_callback_registered(self, stream: HeatmapStream) -> None:
        stream.add_callback("cb", lambda b: None)
        assert "cb" in stream.callback_names

    def test_remove_callback_unregistered(self, stream: HeatmapStream) -> None:
        stream.add_callback("cb", lambda b: None)
        stream.remove_callback("cb")
        assert "cb" not in stream.callback_names

    def test_remove_unknown_is_silent(self, stream: HeatmapStream) -> None:
        stream.remove_callback("ghost")  # should not raise

    def test_non_callable_raises(self, stream: HeatmapStream) -> None:
        with pytest.raises(TypeError):
            stream.add_callback("bad", 42)  # type: ignore[arg-type]

    def test_empty_name_raises(self, stream: HeatmapStream) -> None:
        with pytest.raises(ValueError):
            stream.add_callback("", lambda b: None)


class TestFeed:
    def test_feed_updates_builder(self, stream: HeatmapStream) -> None:
        stream.feed(_make_event("obj1", "fence_a", EventType.ENTER))
        assert stream.builder.count("obj1", "fence_a") == 1

    def test_callback_invoked_on_feed(self, stream: HeatmapStream) -> None:
        received = []
        stream.add_callback("spy", lambda b: received.append(b.count("obj1", "fence_a")))
        stream.feed(_make_event("obj1", "fence_a", EventType.ENTER))
        assert received == [1]

    def test_multiple_callbacks_all_invoked(self, stream: HeatmapStream) -> None:
        calls: dict = {"a": 0, "b": 0}
        stream.add_callback("a", lambda b: calls.update(a=calls["a"] + 1))
        stream.add_callback("b", lambda b: calls.update(b=calls["b"] + 1))
        stream.feed(_make_event("obj1", "fence_a", EventType.ENTER))
        assert calls == {"a": 1, "b": 1}

    def test_reset_delegates_to_builder(self, stream: HeatmapStream) -> None:
        stream.feed(_make_event("obj1", "fence_a", EventType.ENTER))
        stream.reset()
        assert stream.builder.count("obj1", "fence_a") == 0
