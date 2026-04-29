"""Tests for Point, Geofence, and GeofenceChecker core functionality."""

import pytest

from geofence_watch.point import Point
from geofence_watch.fence import Geofence
from geofence_watch.checker import GeofenceChecker

# Simple square: lon -1..1, lat -1..1
SQUARE_COORDS = [
    [-1.0, -1.0],
    [1.0, -1.0],
    [1.0, 1.0],
    [-1.0, 1.0],
    [-1.0, -1.0],  # closed ring
]

SQUARE_GEOJSON = {
    "type": "Feature",
    "properties": {"name": "test-square"},
    "geometry": {
        "type": "Polygon",
        "coordinates": [SQUARE_COORDS],
    },
}


class TestPoint:
    def test_valid_point(self):
        p = Point(latitude=51.5, longitude=-0.1, label="London")
        assert p.latitude == 51.5
        assert p.longitude == -0.1
        assert p.label == "London"

    def test_as_tuple_is_lon_lat(self):
        p = Point(latitude=10.0, longitude=20.0)
        assert p.as_tuple() == (20.0, 10.0)

    def test_invalid_latitude(self):
        with pytest.raises(ValueError, match="Latitude"):
            Point(latitude=91.0, longitude=0.0)

    def test_invalid_longitude(self):
        with pytest.raises(ValueError, match="Longitude"):
            Point(latitude=0.0, longitude=181.0)


class TestGeofence:
    def test_from_coordinates(self):
        fence = Geofence(name="square", coordinates=SQUARE_COORDS)
        assert fence.name == "square"
        assert len(fence.ring) == 5

    def test_from_geojson_feature(self):
        fence = Geofence.from_geojson(SQUARE_GEOJSON)
        assert fence.name == "test-square"

    def test_from_geojson_polygon(self):
        polygon = SQUARE_GEOJSON["geometry"]
        fence = Geofence.from_geojson(polygon, name="poly")
        assert fence.name == "poly"

    def test_invalid_geojson_type(self):
        with pytest.raises(ValueError, match="Unsupported"):
            Geofence.from_geojson({"type": "Point", "coordinates": [0, 0]})

    def test_too_few_coordinates(self):
        with pytest.raises(ValueError, match="at least 4"):
            Geofence(name="tiny", coordinates=[[0, 0], [1, 0], [0, 0]])


class TestGeofenceChecker:
    def setup_method(self):
        self.fence = Geofence(name="square", coordinates=SQUARE_COORDS)
        self.checker = GeofenceChecker()
        self.checker.register(self.fence)

    def test_point_inside(self):
        p = Point(latitude=0.0, longitude=0.0)
        assert self.checker.contains(self.fence, p) is True

    def test_point_outside(self):
        p = Point(latitude=5.0, longitude=5.0)
        assert self.checker.contains(self.fence, p) is False

    def test_check_point_returns_dict(self):
        p = Point(latitude=0.5, longitude=0.5)
        result = self.checker.check_point(p)
        assert result == {"square": True}

    def test_matching_fences_generator(self):
        p = Point(latitude=0.0, longitude=0.0)
        matches = list(self.checker.matching_fences(p))
        assert "square" in matches

    def test_unregister_fence(self):
        self.checker.unregister("square")
        assert "square" not in self.checker.fence_names
