import json
from pathlib import Path
from typing import Dict, Any

class DiskStorageService:
    """Service to handle storing wildfire results locally as GeoJSON files."""
    
    def __init__(self, local_dir: Path):
        self.local_dir = local_dir
        # Ensure local storage directory exists
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def store_geojson(self, filename: str, analysis_results: Dict[str, Any]) -> str:
        """
        Transforms analysis results to GeoJSON FeatureCollection and writes to disk.
        Returns the absolute path of the written file.
        """
        features = []
        for fire in analysis_results.get("detected_fires", []):
            lat = fire.get("latitude")
            lon = fire.get("longitude")
            
            # Ensure valid coordinates for GeoJSON
            if lat is not None and lon is not None:
                # Copy properties and remove lat/lon from properties to avoid duplication
                properties = fire.copy()
                properties.pop("latitude", None)
                properties.pop("longitude", None)
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]  # Longitude first in GeoJSON
                    },
                    "properties": properties
                }
                features.append(feature)
                
        geojson_payload = {
            "type": "FeatureCollection",
            "metadata": {
                "total_records_processed": analysis_results.get("total_records_processed", 0),
                "detected_fires_count": analysis_results.get("detected_fires_count", 0),
                "alert_triggered": analysis_results.get("alert_triggered", False)
            },
            "features": features
        }
        
        local_path = self.local_dir / filename
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(geojson_payload, f, indent=2, default=str)
            
        print(f"GeoJSON report saved locally: {local_path}")
        return str(local_path.resolve())
