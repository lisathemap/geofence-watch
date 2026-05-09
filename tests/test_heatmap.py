"""Tests for HeatmapBuilder and HeatmapCell."""
import pytest

from geofence_watch.event import EventType, GeofenceEvent
from geofence_watch.heatmap import HeatmapBuilder, HeatmapCell
from geofence_watch.point import Point


def _make_event(obj: str, fence: str, etype: EventType) -> GeofenceEvent:
    return GeofenceEvent(
        object_id=obj,
        fence_name=fence,
        event_type=etype,
        point=Point(0.0, 0.0),
    )


@pytest.fixture()
def builder() -> HeatmapBuilder:
    return HeatmapBuilder()


class TestHeatmapBuilderInit:
    def test_starts_empty(self, builder: HeatmapBuilder) -> None:
        assert builder.cells() == []

    def test_count_unknown_pair_is_zero(self, builder: HeatmapBuilder) -> None:
        assert builder.count("obj1", "fence_a") == 0


class TestIngest:
    def test_enter_increments_count(self, builder: HeatmapBuilder) -> None:
        builder.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
        assert builder.count("obj1", "fence_a") == 1

    def test_exit_does_not_increment(self, builder: HeatmapBuilder) -> None:
        builder.ingest(_make_event("obj1", "fence_a", EventType.EXIT))
        assert builder.count("obj1", "fence_a") == 0

    def test_multiple_enters_accumulate(self, builder: HeatmapBuilder) -> None:
        for _ in range(4):
            builder.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
        assert builder.count("obj1", "fence_a") == 4

    def test_different_objects_tracked_separately(self, builder: HeatmapBuilder) -> None:
        builder.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
        builder.ingest(_make_event("obj2", "fence_a", EventType.ENTER))
        builder.ingest(_make_event("obj2", "fence_a", EventType.ENTER))
        assert builder.count("obj1", "fence_a") == 1
        assert builder.count("obj2", "fence_a") == 2

    def test_non_event_raises(self, builder: HeatmapBuilder) -> None:
        with pytest.raises(TypeError):
            builder.ingest("not-an-event")  # type: ignore[arg-type]


class TestTopFences:
    def test_top_fences_ordering(self, builder: HeatmapBuilder) -> None:
        for _ in range(3):
            builder.ingest(_make_event("o", "fence_b", EventType.ENTER))
        builder.ingest(_make_event("o", "fence_a", EventType.ENTER))
        top = builder.top_fences(2)
        assert top[0] == ("fence_b", 3)
        assert top[1] == ("fence_a", 1)

    def test_top_fences_respects_n(self, builder: HeatmapBuilder) -> None:
        for name in ("a", "b", "c", "d"):
            builder.ingest(_make_event("o", name, EventType.ENTER))
        assert len(builder.top_fences(2)) == 2

    def test_top_fences_invalid_n(self, builder: HeatmapBuilder) -> None:
        with pytest.raises(ValueError):
            builder.top_fences(0)


class TestCells:
    def test_cells_returns_correct_type(self, builder: HeatmapBuilder) -> None:
        builder.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
        cells = builder.cells()
        assert all(isinstance(c, HeatmapCell) for c in cells)

    def test_cells_filtered_by_fence(self, builder: HeatmapBuilder) -> None:
        builder.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
        builder.ingest(_make_event("obj1", "fence_b", EventType.ENTER))
        cells = builder.cells(fence_name="fence_a")
        assert len(cells) == 1
        assert cells[0].fence_name == "fence_a"

    def test_reset_clears_all(self, builder: HeatmapBuilder) -> None:
        builder.ingest(_make_event("obj1", "fence_a", EventType.ENTER))
        builder.reset()
        assert builder.cells() == []
        assert builder.count("obj1", "fence_a") == 0
