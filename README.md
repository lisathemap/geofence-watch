# geofence-watch

Lightweight Python library for evaluating real-time coordinate streams against GeoJSON polygon boundaries.

---

## Installation

```bash
pip install geofence-watch
```

---

## Usage

```python
from geofence_watch import GeofenceWatcher

# Load a GeoJSON polygon boundary
watcher = GeofenceWatcher.from_file("boundaries.geojson")

# Evaluate a single coordinate
lat, lon = 37.7749, -122.4194
if watcher.contains(lat, lon):
    print("Coordinate is inside the geofence.")
else:
    print("Coordinate is outside the geofence.")

# Stream coordinates in real time
coordinates = [(37.7749, -122.4194), (34.0522, -118.2437), (40.7128, -74.0060)]

for lat, lon in coordinates:
    status = watcher.check(lat, lon)
    print(f"({lat}, {lon}) -> {status.event}")  # ENTER, INSIDE, EXIT, OUTSIDE
```

### Loading from a GeoJSON string

```python
import json
from geofence_watch import GeofenceWatcher

geojson = json.loads('{"type": "Polygon", "coordinates": [...]}')
watcher = GeofenceWatcher.from_geojson(geojson)
```

---

## Features

- Supports GeoJSON `Polygon` and `MultiPolygon` geometries
- Emits state-change events: `ENTER`, `INSIDE`, `EXIT`, `OUTSIDE`
- Designed for high-frequency coordinate streams
- Zero heavy dependencies — built on `shapely`

---

## Requirements

- Python 3.8+
- `shapely >= 2.0`

---

## License

This project is licensed under the [MIT License](LICENSE).