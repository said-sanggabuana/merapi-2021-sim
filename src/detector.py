from typing import List, Dict, Any, Optional

class WildfireDetector:
    """Logic to process, filter, and flag wildfire detections from raw FIRMS data."""
    
    def __init__(self, min_confidence: str = "nominal"):
        # min_confidence can be 'low', 'nominal', 'high' (for VIIRS)
        # or a numeric threshold string like '80' (for MODIS)
        self.min_confidence = min_confidence.strip().lower()

    def _is_confidence_satisfied(self, record: Dict[str, Any]) -> bool:
        """Determines if a fire point satisfies the minimum confidence threshold."""
        conf_val = record.get("confidence")
        if conf_val is None:
            return False
            
        conf_str = str(conf_val).strip().lower()
        
        # If threshold is numeric (MODIS percentage, e.g., "80")
        if self.min_confidence.isdigit():
            threshold = int(self.min_confidence)
            try:
                # If the record confidence is numeric (MODIS)
                if conf_str.isdigit():
                    return int(conf_str) >= threshold
                # If record is VIIRS (l/n/h) but threshold is numeric, map them roughly
                # l -> 30%, n -> 70%, h -> 95%
                mapping = {"l": 30, "low": 30, "n": 70, "nominal": 70, "h": 95, "high": 95}
                return mapping.get(conf_str, 0) >= threshold
            except ValueError:
                return False
                
        # If threshold is string-based (VIIRS, e.g., "low", "nominal", "high")
        # VIIRS levels: l (low), n (nominal), h (high)
        val_map = {"l": 1, "low": 1, "n": 2, "nominal": 2, "h": 3, "high": 3}
        
        rec_val = val_map.get(conf_str, 0)
        # If record is MODIS (0-100%) but threshold is string-based, map back
        if conf_str.isdigit():
            pct = int(conf_str)
            if pct >= 85:
                rec_val = 3 # high
            elif pct >= 40:
                rec_val = 2 # nominal
            else:
                rec_val = 1 # low
                
        thresh_val = val_map.get(self.min_confidence, 2) # default to nominal if invalid
        return rec_val >= thresh_val

    def filter_fires(
        self,
        records: List[Dict[str, Any]],
        bbox: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filters raw FIRMS fire records based on confidence threshold and optional geographic bounding box.
        
        bbox parameter format:
            {
                "min_lat": float,
                "max_lat": float,
                "min_lon": float,
                "max_lon": float
            }
        """
        filtered_fires = []
        for record in records:
            # Check confidence
            if not self._is_confidence_satisfied(record):
                continue
                
            # Check geographic bounding box if supplied
            if bbox:
                lat = record.get("latitude")
                lon = record.get("longitude")
                if lat is None or lon is None:
                    continue
                
                # Verify coordinates fall within bounds
                if not (bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lon"] <= lon <= bbox["max_lon"]):
                    continue
            
            filtered_fires.append(record)
            
        return filtered_fires

    def analyze(
        self,
        records: List[Dict[str, Any]],
        bbox: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes fire records and returns a summary payload.
        """
        filtered = self.filter_fires(records, bbox=bbox)
        
        return {
            "total_records_processed": len(records),
            "detected_fires_count": len(filtered),
            "alert_triggered": len(filtered) > 0,
            "detected_fires": filtered
        }
