import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load local .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Config:
    """Application configuration loaded from environment variables or .env."""
    
    NASA_FIRMS_MAP_KEY = os.getenv("NASA_FIRMS_MAP_KEY", "").strip()
    
    # NASA FIRMS API settings
    # Default country code to monitor (e.g., 'USA' or 'global' or 'CAN')
    FIRE_DATA_COUNTRY = os.getenv("FIRE_DATA_COUNTRY", "USA").strip()
    
    # Default data source: MODIS_NRT, VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT
    FIRE_DATA_SOURCE = os.getenv("FIRE_DATA_SOURCE", "VIIRS_SNPP_NRT").strip()
    
    # Alert criteria
    # Minimum confidence level to trigger alerts ('low', 'nominal', 'high' for VIIRS; or 0-100 for MODIS)
    MIN_CONFIDENCE = os.getenv("MIN_CONFIDENCE", "nominal").strip().lower()
    
    # Storage settings
    LOCAL_STORAGE_DIR = BASE_DIR / os.getenv("LOCAL_STORAGE_DIR", "data")
    
    # Bounding box settings for dynamic geofencing
    BBOX_MIN_LON = os.getenv("BBOX_MIN_LON", "").strip()
    BBOX_MIN_LAT = os.getenv("BBOX_MIN_LAT", "").strip()
    BBOX_MAX_LON = os.getenv("BBOX_MAX_LON", "").strip()
    BBOX_MAX_LAT = os.getenv("BBOX_MAX_LAT", "").strip()

    @classmethod
    def validate(cls):
        """Validate configuration settings. Returns True if valid, raises ValueError otherwise."""
        if not cls.NASA_FIRMS_MAP_KEY:
            print("WARNING: NASA_FIRMS_MAP_KEY is not set. API calls will fail without a valid key.")
        
        # Ensure local storage directory exists
        cls.LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        return True
