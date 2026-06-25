import json
from pathlib import Path
import pytest

def get_geojson_files():
    """Scans the local data/ directory for any generated .geojson layers."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    if not data_dir.exists():
        return []
    files = list(data_dir.glob("*.geojson"))
    return [str(f) for f in files]

geojson_files = get_geojson_files()

def extract_vertices(geometry):
    """Recursively extracts all coordinate vertices from GeoJSON geometry types."""
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    
    vertices = []
    if geom_type == "Point":
        vertices.append(coords)
    elif geom_type in ("LineString", "MultiPoint"):
        vertices.extend(coords)
    elif geom_type in ("Polygon", "MultiLineString"):
        for ring in coords:
            vertices.extend(ring)
    elif geom_type == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                vertices.extend(ring)
    return vertices

@pytest.mark.skipif(not geojson_files, reason="No .geojson files found in the data/ directory to validate.")
@pytest.mark.parametrize("filepath", geojson_files)
def test_geojson_integrity(filepath):
    """
    Scaffolds production-grade checks verifying JSON parsing,
    RFC 7946 compliance, geometry validity, bounding box geofence bounds,
    and expected properties.
    """
    path = Path(filepath)
    filename = path.name
    
    # 1. File I/O Integrity (parsable JSON payload structure)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"File {filename} is not a valid parsable JSON structure: {e}")

    # 2. RFC 7946 Compliance (root type must equal 'FeatureCollection', containing a valid 'features' list)
    assert data.get("type") == "FeatureCollection", f"[{filename}] Root 'type' must be 'FeatureCollection'"
    assert isinstance(data.get("features"), list), f"[{filename}] Root 'features' key must contain a list array"

    # Mount Merapi BBOX: longitude 110.34 to 110.54 and latitude -7.63 to -7.44 (accommodating the 10km buffer)
    min_lon, max_lon = 110.34, 110.54
    min_lat, max_lat = -7.63, -7.44
    
    features = data.get("features")
    for idx, feature in enumerate(features):
        assert feature.get("type") == "Feature", f"[{filename}] Feature at index {idx} must have 'type': 'Feature'"
        
        geometry = feature.get("geometry")
        assert isinstance(geometry, dict), f"[{filename}] Feature {idx} must contain a nested 'geometry' map"
        assert "type" in geometry, f"[{filename}] Feature {idx} geometry is missing 'type'"
        assert "coordinates" in geometry, f"[{filename}] Feature {idx} geometry is missing 'coordinates'"
        
        # Extract coordinates and assert containment
        vertices = extract_vertices(geometry)
        assert len(vertices) > 0, f"[{filename}] Feature {idx} geometry contains no vertices"
        
        for v_idx, vertex in enumerate(vertices):
            assert len(vertex) >= 2, f"[{filename}] Vertex {v_idx} in Feature {idx} must have [longitude, latitude]"
            lon, lat = vertex[0], vertex[1]
            
            # Boundary assertions
            assert min_lon <= lon <= max_lon, f"[{filename}] Longitude {lon} in feature {idx} (vertex {v_idx}) exceeds Mount Merapi window [{min_lon}, {max_lon}]"
            assert min_lat <= lat <= max_lat, f"[{filename}] Latitude {lat} in feature {idx} (vertex {v_idx}) exceeds Mount Merapi window [{min_lat}, {max_lat}]"

        # 4. Attribute Properties Schema Check (verify detection_timestamp and burn_severity are initialized)
        properties = feature.get("properties")
        assert isinstance(properties, dict), f"[{filename}] Feature {idx} must contain a nested 'properties' map"
        
        assert "detection_timestamp" in properties, f"[{filename}] Feature {idx} properties must contain 'detection_timestamp'"
        assert "burn_severity" in properties, f"[{filename}] Feature {idx} properties must contain 'burn_severity'"
        
        assert properties.get("detection_timestamp") is not None, f"[{filename}] Feature {idx} 'detection_timestamp' must be initialized"
        assert properties.get("burn_severity") is not None, f"[{filename}] Feature {idx} 'burn_severity' must be initialized"
        
        # Verify they are non-empty strings
        assert str(properties.get("detection_timestamp")).strip() != "", f"[{filename}] Feature {idx} 'detection_timestamp' cannot be empty"
        assert str(properties.get("burn_severity")).strip() != "", f"[{filename}] Feature {idx} 'burn_severity' cannot be empty"
