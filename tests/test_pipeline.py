"""Tests for geofence_watch.pipeline.EventPipeline."""

import pytest
from datetime import datetime, timezone

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.pipeline import EventPipeline
from geofence_watch.point import Point


def _make_event(
    obj_id: str = "obj-1",
    fence: str = "zone-a",
    etype: EventType = EventType.ENTER,
) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=obj_id,
        fence_name=fence,
        event_type=etype,
        point=Point(0.0, 0.0),
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def pipeline() -> EventPipeline:
    return EventPipeline()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestEventPipelineInit:
    def test_starts_with_no_stages(self, pipeline: EventPipeline) -> None:
        assert pipeline.stage_count == 0

    def test_add_stage_increments_count(self, pipeline: EventPipeline) -> None:
        pipeline.add_stage(lambda e: e)
        assert pipeline.stage_count == 1

    def test_add_non_callable_raises(self, pipeline: EventPipeline) -> None:
        with pytest.raises(TypeError):
            pipeline.add_stage("not_a_function")  # type: ignore[arg-type]

    def test_remove_stage_decrements_count(self, pipeline: EventPipeline) -> None:
        fn = lambda e: e
        pipeline.add_stage(fn)
        pipeline.remove_stage(fn)
        assert pipeline.stage_count == 0

    def test_remove_unknown_stage_raises(self, pipeline: EventPipeline) -> None:
        with pytest.raises(KeyError):
            pipeline.remove_stage(lambda e: e)


# ---------------------------------------------------------------------------
# Processing — pass-through
# ---------------------------------------------------------------------------

class TestEventPipelineProcess:
    def test_no_stages_returns_event(self, pipeline: EventPipeline) -> None:
        evt = _make_event()
        assert pipeline.process(evt) is evt

    def test_stage_can_transform_event(self, pipeline: EventPipeline) -> None:
        def retag(e: GeofenceEvent) -> GeofenceEvent:
            return GeofenceEvent(
                object_id="renamed",
                fence_name=e.fence_name,
                event_type=e.event_type,
                point=e.point,
                timestamp=e.timestamp,
            )

        pipeline.add_stage(retag)
        result = pipeline.process(_make_event())
        assert result is not None
        assert result.object_id == "renamed"

    def test_stage_returning_none_drops_event(self, pipeline: EventPipeline) -> None:
        pipeline.add_stage(lambda e: None)
        assert pipeline.process(_make_event()) is None

    def test_stages_after_drop_not_called(self, pipeline: EventPipeline) -> None:
        called = []
        pipeline.add_stage(lambda e: None)
        pipeline.add_stage(lambda e: called.append(e) or e)  # type: ignore
        pipeline.process(_make_event())
        assert called == []

    def test_multiple_stages_applied_in_order(self, pipeline: EventPipeline) -> None:
        order: list[int] = []
        pipeline.add_stage(lambda e: (order.append(1), e)[1])
        pipeline.add_stage(lambda e: (order.append(2), e)[1])
        pipeline.process(_make_event())
        assert order == [1, 2]


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

class TestEventPipelineCallbacks:
    def test_callback_receives_surviving_event(self, pipeline: EventPipeline) -> None:
        received: list[GeofenceEvent] = []
        pipeline.add_callback(received.append)
        evt = _make_event()
        pipeline.process(evt)
        assert received == [evt]

    def test_callback_not_called_when_event_dropped(self, pipeline: EventPipeline) -> None:
        received: list[GeofenceEvent] = []
        pipeline.add_stage(lambda e: None)
        pipeline.add_callback(received.append)
        pipeline.process(_make_event())
        assert received == []

    def test_add_non_callable_callback_raises(self, pipeline: EventPipeline) -> None:
        with pytest.raises(TypeError):
            pipeline.add_callback(42)  # type: ignore[arg-type]

    def test_remove_unknown_callback_raises(self, pipeline: EventPipeline) -> None:
        with pytest.raises(KeyError):
            pipeline.remove_callback(lambda e: None)

    def test_remove_callback_stops_delivery(self, pipeline: EventPipeline) -> None:
        received: list[GeofenceEvent] = []
        cb = received.append
        pipeline.add_callback(cb)
        pipeline.remove_callback(cb)
        pipeline.process(_make_event())
        assert received == []
