"""Geofence model built from a GeoJSON polygon definition."""

from __future__ import annotations

from typing import Any

from geofence_watch.point import Point


class Geofence:
    """Represents a polygon geofence loaded from a GeoJSON feature or geometry."""

    def __init__(self, name: str, coordinates: list[list[float]]) -> None:
        """
        Args:
            name: Human-readable identifier for this fence.
            coordinates: List of [longitude, latitude] pairs forming a closed ring.
        """
        if len(coordinates) < 4:
            raise ValueError("A polygon ring must have at least 4 coordinate pairs (closed ring).")
        self.name = name
        self._ring: list[tuple[float, float]] = [(c[0], c[1]) for c in coordinates]

    @classmethod
    def from_geojson(cls, geojson: dict[str, Any], name: str = "unnamed") -> Geofence:
        """Construct a Geofence from a GeoJSON Feature or Polygon geometry dict."""
        geo_type = geojson.get("type")
        if geo_type == "Feature":
            geometry = geojson.get("geometry", {})
            name = geojson.get("properties", {}).get("name", name)
        elif geo_type == "Polygon":
            geometry = geojson
        else:
            raise ValueError(f"Unsupported GeoJSON type: {geo_type!r}. Expected 'Feature' or 'Polygon'.")

        coords = geometry.get("coordinates")
        if not coords or not isinstance(coords, list):
            raise ValueError("GeoJSON geometry missing valid 'coordinates'.")

        # Use the exterior ring (index 0)
        return cls(name=name, coordinates=coords[0])

    @property
    def ring(self) -> list[tuple[float, float]]:
        """Return the exterior ring as a list of (lon, lat) tuples."""
        return self._ring

    def __repr__(self) -> str:
        return f"Geofence(name={self.name!r}, vertices={len(self._ring)})"
