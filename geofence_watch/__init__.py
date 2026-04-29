"""geofence-watch: Lightweight Python library for evaluating real-time coordinate streams against GeoJSON polygon boundaries."""

from geofence_watch.fence import Geofence
from geofence_watch.point import Point
from geofence_watch.checker import GeofenceChecker

__version__ = "0.1.0"
__all__ = ["Geofence", "Point", "GeofenceChecker"]
