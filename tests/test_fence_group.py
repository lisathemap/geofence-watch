"""Tests for FenceGroup and FenceGroupStream."""
from __future__ import annotations

import pytest

from geofence_watch.fence import Geofence
from geofence_watch.fence_group import FenceGroup
from geofence_watch.fence_group_stream import FenceGroupStream
from geofence_watch.point import Point

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _square_fence(name: str, offset: float = 0.0) -> Geofence:
    """Return a small square Geofence centred near (0, 0)."""
    coords = [
        [offset - 1, offset - 1],
        [offset + 1, offset - 1],
        [offset + 1, offset + 1],
        [offset - 1, offset + 1],
        [offset - 1, offset - 1],
    ]
    geojson = {
        "type": "Feature",
        "properties": {"name": name},
        "geometry": {"type": "Polygon", "coordinates": [coords]},
    }
    return Geofence.from_geojson(geojson)


@pytest.fixture()
def group() -> FenceGroup:
    g = FenceGroup("test-group")
    g.add(_square_fence("alpha"))
    g.add(_square_fence("beta", offset=0.5))
    return g


@pytest.fixture()
def stream(group: FenceGroup) -> FenceGroupStream:
    return FenceGroupStream(group)


# ---------------------------------------------------------------------------
# FenceGroup tests
# ---------------------------------------------------------------------------

class TestFenceGroupInit:
    def test_name_stored(self):
        g = FenceGroup("my-group")
        assert g.name == "my-group"

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            FenceGroup("")

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError):
            FenceGroup("   ")

    def test_starts_empty(self):
        g = FenceGroup("g")
        assert len(g) == 0
        assert g.fence_names == []


def test_add_and_len(group):
    assert len(group) == 2


def test_add_non_fence_raises():
    g = FenceGroup("g")
    with pytest.raises(TypeError):
        g.add("not-a-fence")  # type: ignore[arg-type]


def test_remove_existing(group):
    group.remove("alpha")
    assert "alpha" not in group.fence_names
    assert len(group) == 1


def test_remove_missing_raises(group):
    with pytest.raises(KeyError):
        group.remove("nonexistent")


def test_get_existing(group):
    f = group.get("alpha")
    assert isinstance(f, Geofence)
    assert f.name == "alpha"


def test_get_missing_raises(group):
    with pytest.raises(KeyError):
        group.get("ghost")


def test_contains_any_inside(group):
    p = Point(lon=0.0, lat=0.0)
    assert group.contains_any(p) is True


def test_contains_any_outside(group):
    p = Point(lon=50.0, lat=50.0)
    assert group.contains_any(p) is False


def test_contains_all_false_when_only_one_matches():
    g = FenceGroup("g")
    g.add(_square_fence("near", offset=0.0))
    g.add(_square_fence("far", offset=10.0))
    p = Point(lon=0.0, lat=0.0)
    assert g.contains_all(p) is False


def test_contains_all_empty_group_returns_false():
    g = FenceGroup("empty")
    assert g.contains_all(Point(lon=0.0, lat=0.0)) is False


def test_matching_fences_returns_correct_subset(group):
    p = Point(lon=0.0, lat=0.0)
    matches = group.matching_fences(p)
    names = {f.name for f in matches}
    assert "alpha" in names


def test_iter_yields_all_fences(group):
    fences = list(group)
    assert len(fences) == 2


# ---------------------------------------------------------------------------
# FenceGroupStream tests
# ---------------------------------------------------------------------------

class TestFenceGroupStreamInit:
    def test_group_property(self, stream, group):
        assert stream.group is group

    def test_no_callbacks_initially(self, stream):
        assert stream.callback_names == []

    def test_non_group_raises(self):
        with pytest.raises(TypeError):
            FenceGroupStream("not-a-group")  # type: ignore[arg-type]


def test_add_callback(stream):
    stream.add_callback("cb", lambda p, m: None)
    assert "cb" in stream.callback_names


def test_add_non_callable_raises(stream):
    with pytest.raises(TypeError):
        stream.add_callback("bad", "not-callable")  # type: ignore[arg-type]


def test_add_empty_name_raises(stream):
    with pytest.raises(ValueError):
        stream.add_callback("", lambda p, m: None)


def test_remove_callback(stream):
    stream.add_callback("cb", lambda p, m: None)
    stream.remove_callback("cb")
    assert "cb" not in stream.callback_names


def test_remove_missing_callback_raises(stream):
    with pytest.raises(KeyError):
        stream.remove_callback("ghost")


def test_process_returns_matches(stream):
    p = Point(lon=0.0, lat=0.0)
    matches = stream.process(p)
    assert isinstance(matches, list)
    assert all(isinstance(f, Geofence) for f in matches)


def test_process_invokes_callback(stream):
    received: list = []
    stream.add_callback("spy", lambda p, m: received.append((p, m)))
    p = Point(lon=0.0, lat=0.0)
    stream.process(p)
    assert len(received) == 1
    assert received[0][0] is p


def test_process_non_point_raises(stream):
    with pytest.raises(TypeError):
        stream.process((0.0, 0.0))  # type: ignore[arg-type]
