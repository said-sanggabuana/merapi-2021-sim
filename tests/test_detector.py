import pytest
import sys
from pathlib import Path

# Add src folder to python path so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detector import WildfireDetector

@pytest.fixture
def sample_fires():
    return [
        {
            "latitude": 34.05,
            "longitude": -118.24,
            "confidence": "high",
            "frp": 15.0
        },
        {
            "latitude": 37.77,
            "longitude": -122.41,
            "confidence": "low",
            "frp": 3.0
        },
        {
            "latitude": 40.71,
            "longitude": -74.00,
            "confidence": "nominal",
            "frp": 8.0
        },
        {
            "latitude": 45.0,
            "longitude": -100.0,
            "confidence": "85",  # MODIS style
            "frp": 22.0
        },
        {
            "latitude": 46.0,
            "longitude": -101.0,
            "confidence": "30",  # MODIS style (low)
            "frp": 1.5
        }
    ]

def test_detector_confidence_filtering(sample_fires):
    # Test threshold = nominal (should exclude low, include nominal, high, and 85%)
    detector_nominal = WildfireDetector(min_confidence="nominal")
    filtered = detector_nominal.filter_fires(sample_fires)
    
    assert len(filtered) == 3
    # Check that 'high', 'nominal', and '85' are in, 'low' and '30' are out
    confidences = [f["confidence"] for f in filtered]
    assert "high" in confidences
    assert "nominal" in confidences
    assert "85" in confidences
    assert "low" not in confidences
    assert "30" not in confidences

def test_detector_high_confidence_only(sample_fires):
    detector_high = WildfireDetector(min_confidence="high")
    filtered = detector_high.filter_fires(sample_fires)
    
    assert len(filtered) == 2
    confidences = [f["confidence"] for f in filtered]
    assert "high" in confidences
    assert "85" in confidences

def test_detector_numeric_threshold(sample_fires):
    # Test numeric threshold (e.g. 80%)
    detector_numeric = WildfireDetector(min_confidence="80")
    filtered = detector_numeric.filter_fires(sample_fires)
    
    assert len(filtered) == 2
    confidences = [f["confidence"] for f in filtered]
    # 'high' mapped to 95%, '85' mapped to 85%
    assert "high" in confidences
    assert "85" in confidences

def test_detector_geofence_filtering(sample_fires):
    detector = WildfireDetector(min_confidence="low") # include everything
    
    # Bounding box containing only California-ish coordinates (e.g., -118, -122)
    california_bbox = {
        "min_lat": 32.0,
        "max_lat": 42.0,
        "min_lon": -125.0,
        "max_lon": -115.0
    }
    
    filtered = detector.filter_fires(sample_fires, bbox=california_bbox)
    # Should include (34.05, -118.24) and (37.77, -122.41)
    assert len(filtered) == 2
    latitudes = [f["latitude"] for f in filtered]
    assert 34.05 in latitudes
    assert 37.77 in latitudes

def test_detector_analyze_summary(sample_fires):
    detector = WildfireDetector(min_confidence="nominal")
    results = detector.analyze(sample_fires)
    
    assert results["total_records_processed"] == 5
    assert results["detected_fires_count"] == 3
    assert results["alert_triggered"] is True
    assert len(results["detected_fires"]) == 3

def test_disk_storage_service_geojson(tmp_path, sample_fires):
    from storage_service import DiskStorageService
    from detector import WildfireDetector
    import json
    
    # Instantiate service using temporary test directory
    storage_service = DiskStorageService(local_dir=tmp_path)
    
    detector = WildfireDetector(min_confidence="nominal")
    analysis_results = detector.analyze(sample_fires)
    
    filename = "test_report.geojson"
    file_path_str = storage_service.store_geojson(filename, analysis_results)
    
    # Check file exists and coordinates are in GeoJSON order [longitude, latitude]
    file_path = Path(file_path_str)
    assert file_path.exists()
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["type"] == "FeatureCollection"
    assert "metadata" in data
    assert data["metadata"]["total_records_processed"] == 5
    assert len(data["features"]) == 3
    
    # Verify longitude first
    first_feature = data["features"][0]
    assert first_feature["type"] == "Feature"
    assert first_feature["geometry"]["type"] == "Point"
    # high confidence fire: (34.05, -118.24) -> [-118.24, 34.05]
    assert first_feature["geometry"]["coordinates"] == [-118.24, 34.05]
    assert "latitude" not in first_feature["properties"]
    assert "longitude" not in first_feature["properties"]
    assert first_feature["properties"]["confidence"] == "high"

