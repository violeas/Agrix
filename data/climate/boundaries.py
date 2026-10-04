"""Read authoritative GeoJSON boundaries without spatially inventing labels.

Configure AGRISHIELD_BOUNDARY_GEOJSON with an official/local GeoJSON Feature or
FeatureCollection. Coordinates use GeoJSON order (longitude, latitude). Boundary
matching enriches a point; it does not aggregate grid weather into an area forecast.
"""
from functools import lru_cache
import json
from pathlib import Path


PROPERTY_ALIASES = {
    "state": ("state", "state_name", "stname"),
    "district": ("district", "district_name", "dtname"),
    "block": ("block", "block_name", "mandal", "mandal_name", "subdistrict"),
    "village_cluster": ("panchayat", "panchayat_name", "village_cluster", "village", "village_name"),
    "boundary_id": ("panchayat_code", "village_code", "block_code", "district_code", "gid", "id"),
}


@lru_cache(maxsize=8)
def _load_features(path, modified_ns):
    del modified_ns
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("type") == "FeatureCollection":
        features = payload.get("features") or []
    elif payload.get("type") == "Feature":
        features = [payload]
    else:
        raise ValueError("Boundary GeoJSON must be a Feature or FeatureCollection.")
    return tuple(feature for feature in features if isinstance(feature, dict))


def _on_segment(point, start, end):
    x, y = point
    x1, y1 = start
    x2, y2 = end
    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    if abs(cross) > 1e-10:
        return False
    return min(x1, x2) - 1e-10 <= x <= max(x1, x2) + 1e-10 and min(y1, y2) - 1e-10 <= y <= max(y1, y2) + 1e-10


def _in_ring(point, ring):
    inside = False
    for index, start in enumerate(ring):
        end = ring[(index + 1) % len(ring)]
        if _on_segment(point, start, end):
            return True
        x, y = point
        x1, y1 = start
        x2, y2 = end
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _in_polygon(point, rings):
    if not rings or not _in_ring(point, rings[0]):
        return False
    return not any(_in_ring(point, hole) for hole in rings[1:])


def _contains(point, geometry):
    if not isinstance(geometry, dict):
        return False
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if geometry_type == "Polygon":
        return _in_polygon(point, coordinates)
    if geometry_type == "MultiPolygon":
        return any(_in_polygon(point, polygon) for polygon in coordinates)
    return False


def resolve_boundary(latitude, longitude, path):
    """Return the deepest mapped feature containing a point, if available."""
    if not path:
        return None
    boundary_path = Path(path).expanduser().resolve()
    if not boundary_path.is_file():
        raise FileNotFoundError("Configured administrative boundary GeoJSON was not found.")
    point = (float(longitude), float(latitude))
    features = _load_features(str(boundary_path), boundary_path.stat().st_mtime_ns)
    matches = []
    for feature in features:
        if not _contains(point, feature.get("geometry")):
            continue
        props = feature.get("properties") or {}
        resolved = {}
        for field, aliases in PROPERTY_ALIASES.items():
            value = next((props[key] for key in aliases if props.get(key) not in (None, "")), None)
            if value is not None:
                resolved[field] = str(value)
        resolved["boundary_level"] = next((field for field in ("village_cluster", "block", "district", "state") if resolved.get(field)), "unknown")
        resolved["boundary_source"] = str(boundary_path)
        if resolved:
            matches.append(resolved)
    rank = {"state": 1, "district": 2, "block": 3, "village_cluster": 4}
    return max(matches, key=lambda item: rank.get(item["boundary_level"], 0)) if matches else None
