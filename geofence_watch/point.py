"""Point model representing a geographic coordinate."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Point:
    """Represents a geographic coordinate with latitude and longitude."""

    latitude: float
    longitude: float
    label: Optional[str] = None

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")

    def as_tuple(self) -> tuple[float, float]:
        """Return (longitude, latitude) tuple as used in GeoJSON."""
        return (self.longitude, self.latitude)

    def __repr__(self) -> str:
        label_part = f", label={self.label!r}" if self.label else ""
        return f"Point(lat={self.latitude}, lon={self.longitude}{label_part})"
