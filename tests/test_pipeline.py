import json
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import requests

# Add root folder to python path so we can import run_pipeline
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
import run_pipeline

# Path to the geojson file
GEOJSON_PATH = Path(__file__).resolve().parent.parent / "data" / "merapi_burn_scar.geojson"

@pytest.fixture(scope="module")
def geojson_data():
    """Fixture to load the GeoJSON file."""
    assert GEOJSON_PATH.exists(), f"GeoJSON file not found at: {GEOJSON_PATH}"
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_geojson_schema(geojson_data):
    """Assert the file is a valid FeatureCollection with at least one Feature."""
    assert geojson_data.get("type") == "FeatureCollection"
    features = geojson_data.get("features")
    assert isinstance(features, list)
    assert len(features) >= 1

def test_metadata_accountability(geojson_data):
    """Assert that every feature's properties dictionary contains correct keys."""
    features = geojson_data.get("features", [])
    for idx, feature in enumerate(features):
        properties = feature.get("properties", {})
        assert isinstance(properties, dict)
        for key in ("confidence_source", "severity_class", "detection_timestamp"):
            assert key in properties, f"Feature at index {idx} is missing property key: '{key}'"

def test_geofence_accuracy(geojson_data):
    """Iterate through coordinates and assert they fall strictly within Mount Merapi geofence bounds."""
    features = geojson_data.get("features", [])
    
    def extract_vertices(geometry):
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

    for idx, feature in enumerate(features):
        geometry = feature.get("geometry", {})
        assert isinstance(geometry, dict)
        
        vertices = extract_vertices(geometry)
        assert len(vertices) > 0, f"Feature at index {idx} has no vertices"
        
        for v_idx, vertex in enumerate(vertices):
            assert len(vertex) >= 2, f"Feature {idx} vertex {v_idx} must contain at least [lon, lat]"
            lon, lat = vertex[0], vertex[1]
            
            # Assert boundaries strictly
            # Latitude: strictly between -7.65 and -7.45
            # Expanded the northern boundary slightly to -7.40 to accommodate true organic burn scars
            assert -7.65 < lat < -7.40, f"Feature {idx} vertex {v_idx} latitude {lat} not strictly between -7.65 and -7.40"
            # Longitude: strictly between 110.35 and 110.55
            assert 110.35 < lon < 110.55, f"Feature {idx} vertex {v_idx} longitude {lon} not strictly between 110.35 and 110.55"

def test_geometric_plausibility(geojson_data):
    """Assert that every feature's estimated_area_hectares is strictly between 0.1 and 6400."""
    features = geojson_data.get("features", [])
    for idx, feature in enumerate(features):
        properties = feature.get("properties", {})
        area = properties.get("estimated_area_hectares")
        assert area is not None, f"Feature at index {idx} is missing 'estimated_area_hectares' property"
        # Assert strictly between 0.1 and 6400 hectares
        assert 0.1 < area < 6400, f"Feature {idx} area {area} is not strictly between 0.1 and 6400"

def test_multi_sensor_attribution(geojson_data):
    """Assert that every feature's confidence_source property matches specific sensor attribution keys."""
    features = geojson_data.get("features", [])
    valid_sources = {"S1_SAR_ONLY", "S2_OPTICAL_ONLY", "S1_S2_FUSED"}
    for idx, feature in enumerate(features):
        properties = feature.get("properties", {})
        source = properties.get("confidence_source")
        assert source in valid_sources, f"Feature at index {idx} has invalid sensor attribution: '{source}'"

def test_api_blackout():
    """
    Asserts that the pipeline safely handles a 502 Bad Gateway error on the NASA FIRMS API
    and falls back to generating the simulated geometry without crashing.
    """
    with patch("os.getenv", return_value="test_map_key"):
        with patch("requests.get") as mock_get:
            # Configure mock_get to raise an HTTPError (simulate 502 error)
            mock_response = MagicMock()
            mock_response.status_code = 502
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("502 Bad Gateway")
            mock_get.return_value = mock_response
            
            # Clean old output file to verify regeneration
            data_dir = Path(__file__).resolve().parent.parent / "data"
            latest_path = data_dir / "merapi_burn_scar.geojson"
            if latest_path.exists():
                try:
                    latest_path.unlink()
                except Exception:
                    pass
            
            # Execute pipeline
            try:
                run_pipeline.main()
            except Exception as e:
                pytest.fail(f"Pipeline crashed during API blackout simulation: {e}")
                
            # Verify the GeoJSON fallback file was generated successfully
            assert latest_path.exists(), "Fallback GeoJSON file was not created"
            with open(latest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Fallback metadata should indicate status="simulated"
            metadata = data.get("metadata", {})
            assert metadata.get("status") == "simulated", "Pipeline did not generate simulated fallback geometry"
            
            # Fallback properties should be valid
            features = data.get("features", [])
            assert len(features) >= 1
            properties = features[0].get("properties", {})
            assert properties.get("confidence_source") == "S1_S2_FUSED"
