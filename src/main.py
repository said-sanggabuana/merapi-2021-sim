import sys
import datetime
from config import Config
from firms_client import FIRMSClient
from storage_service import DiskStorageService
from detector import WildfireDetector

def generate_mock_data():
    """Generates mock fire data to simulate API response when key is missing."""
    return [
        {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "bright_ti4": 325.5,
            "acq_date": datetime.date.today().isoformat(),
            "acq_time": "1845",
            "confidence": "high",
            "frp": 12.5
        },
        {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "bright_ti4": 305.2,
            "acq_date": datetime.date.today().isoformat(),
            "acq_time": "1845",
            "confidence": "low",
            "frp": 2.1
        },
        {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "bright_ti4": 318.0,
            "acq_date": datetime.date.today().isoformat(),
            "acq_time": "1900",
            "confidence": "nominal",
            "frp": 8.4
        }
    ]

def main():
    print("=== Wildfire Ingestion & Detection Job Start ===")
    
    # 1. Load and validate configs
    Config.validate()
    
    # Construct bbox from environment variables if present, otherwise default to California
    bbox = None
    if Config.BBOX_MIN_LON and Config.BBOX_MIN_LAT and Config.BBOX_MAX_LON and Config.BBOX_MAX_LAT:
        try:
            bbox = {
                "min_lon": float(Config.BBOX_MIN_LON),
                "min_lat": float(Config.BBOX_MIN_LAT),
                "max_lon": float(Config.BBOX_MAX_LON),
                "max_lat": float(Config.BBOX_MAX_LAT)
            }
            print(f"[INFO] Bounding box loaded dynamically: min_lon={bbox['min_lon']}, min_lat={bbox['min_lat']}, max_lon={bbox['max_lon']}, max_lat={bbox['max_lat']}")
        except ValueError:
            print("[WARNING] Invalid bounding box coordinates in environment variables. Falling back to default geofencing.")
            
    if not bbox:
        # Default geofence (California bbox roughly: lat 32 to 42, lon -124 to -114)
        bbox = {
            "min_lat": 32.0,
            "max_lat": 42.0,
            "min_lon": -124.0,
            "max_lon": -114.0
        }
        print("[INFO] Using default California bounding box geofencing.")
    
    # 2. Fetch active fires
    fires_data = []
    if not Config.NASA_FIRMS_MAP_KEY:
        print("\n[INFO] NASA_FIRMS_MAP_KEY not configured. Generating mock data for testing...")
        fires_data = generate_mock_data()
    else:
        print(f"\n[INFO] Connecting to NASA FIRMS API (Source: {Config.FIRE_DATA_SOURCE}, Country: {Config.FIRE_DATA_COUNTRY})...")
        try:
            client = FIRMSClient(Config.NASA_FIRMS_MAP_KEY)
            fires_data = client.fetch_active_fires(
                country=Config.FIRE_DATA_COUNTRY,
                source=Config.FIRE_DATA_SOURCE,
                days=1
            )
            print(f"[SUCCESS] Successfully retrieved {len(fires_data)} fire records from NASA FIRMS API.")
        except Exception as e:
            print(f"[ERROR] API fetch failed: {e}. Exiting.")
            sys.exit(1)
            
    # 3. Initialize detector and process records
    print(f"[INFO] Initializing Wildfire Detector (Confidence threshold: {Config.MIN_CONFIDENCE})...")
    detector = WildfireDetector(min_confidence=Config.MIN_CONFIDENCE)
    
    # Analyze records within the geofenced bounding box
    analysis_results = detector.analyze(fires_data, bbox=bbox)
    
    print("\n=== Analysis Summary ===")
    print(f"Total Records Evaluated: {analysis_results['total_records_processed']}")
    print(f"Fires matching criteria & geofence: {analysis_results['detected_fires_count']}")
    print(f"Alert Status: {'[ALERT] ACTIVE FIRE ALERT TRIGGERED!' if analysis_results['alert_triggered'] else '[OK] No threat detected.'}")
    
    # 4. Save results as GeoJSON flat-file to disk
    storage_service = DiskStorageService(
        local_dir=Config.LOCAL_STORAGE_DIR
    )
    
    filename = f"wildfire_report_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.geojson"
    destination = storage_service.store_geojson(filename, analysis_results)
    
    print(f"\n[SUCCESS] Run complete. Report saved to: {destination}")
    print("=== Wildfire Ingestion & Detection Job End ===")

if __name__ == "__main__":
    main()
