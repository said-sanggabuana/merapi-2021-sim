import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock, ANY
from pathlib import Path

# Add root folder to python path so we can import run_pipeline
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
import run_pipeline

@patch("ee.Initialize", side_effect=Exception("Forced fallback in test"))
def test_pipeline_historical_coordinates_and_bounds(mock_init):
    """
    Verifies that the run_pipeline execution runs the historical simulation
    with target coordinates (-7.54, 110.44) and correct date/metadata.
    """
    # Clean output data directory before run
    data_dir = Path("data")
    if data_dir.exists():
        for f in data_dir.glob("*.geojson"):
            try:
                f.unlink()
            except Exception:
                pass
                
    # Run the main pipeline (which runs in stateless fallback mode)
    run_pipeline.main()
    
    # Check that the compiled merapi_burn_scar.geojson exists
    latest_path = data_dir / "merapi_burn_scar.geojson"
    assert latest_path.exists()
    
    # Verify the values in the compiled GeoJSON match the historical simulation
    with open(latest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["type"] == "FeatureCollection"
    metadata = data.get("metadata", {})
    if metadata:
        assert metadata.get("status") == "simulated"
        assert metadata.get("centroid_lat") == -7.54
        assert metadata.get("centroid_lon") == 110.44
        assert metadata.get("acq_date") == "2021-02-05"
    
    # Verify feature properties
    features = data.get("features", [])
    assert len(features) > 0
    first_feature = features[0]
    properties = first_feature.get("properties", {})
    assert properties.get("detection_timestamp") == "2021-02-05"

def test_pipeline_earth_engine_classifier_integration():
    """
    Mocks Google Earth Engine API to verify that the Random Forest classifier
    and texture feature calculations are invoked with correct parameters.
    """
    mock_ee = MagicMock()
    
    # Mock pre_fire_col.size().getInfo() and post_fire_col.size().getInfo() to return > 0
    mock_ee.ImageCollection.return_value.map.return_value.filterDate.return_value.size.return_value.getInfo.return_value = 5
    
    dummy_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[110.4, -7.6], [110.5, -7.6], [110.5, -7.52], [110.4, -7.52], [110.4, -7.6]]]
                },
                "properties": {
                    "detection_timestamp": "2021-02-05",
                    "burn_severity": "High",
                    "confidence_source": "S1_S2_FUSED",
                    "estimated_area_hectares": 57.2
                }
            }
        ]
    }
    
    # Mock the chain of calls on post_img to return dummy_geojson on getInfo()
    post_img_mock = mock_ee.ImageCollection.return_value.map.return_value.filterDate.return_value.median.return_value.clip.return_value
    current = post_img_mock
    current = current.select.return_value  # post_img.select(["B4", "B8A", "B12"])
    for _ in range(5):                     # 5 times .addBands(...)
        current = current.addBands.return_value
    current = current.select.return_value  # predictors_img.select(input_properties)
    current = current.classify.return_value  # .classify(classifier)
    current = current.eq.return_value        # classified.eq(1) (optical_mask)
    current = current.Or.return_value        # .Or(sar_burn_mask) (combined_mask)
    current = current.updateMask.return_value # .updateMask(shadow_mask)
    current = current.updateMask.return_value # .updateMask(combined_mask)
    current = current.reduceToVectors.return_value # .reduceToVectors(...)
    mock_ee.Feature.return_value.getInfo.return_value = dummy_geojson["features"][0]
    
    # Patch the ee module
    with patch.dict("sys.modules", {"ee": mock_ee}):
        run_pipeline.main()
        
        # Verify smileRandomForest was instantiated with 50 trees
        mock_ee.Classifier.smileRandomForest.assert_called_once_with(numberOfTrees=50)
        
        # Verify classifier training details
        mock_classifier = mock_ee.Classifier.smileRandomForest.return_value
        mock_classifier.train.assert_called_once()
        train_kwargs = mock_classifier.train.call_args[1]
        assert train_kwargs["classProperty"] == "class"
        assert "dnbr" in train_kwargs["inputProperties"]
        assert "contrast" in train_kwargs["inputProperties"]
        
        # Verify that stratifiedSample was called to generate dynamic training samples
        assert any(
            "stratifiedSample" in str(call) for call in mock_ee.mock_calls
        )
