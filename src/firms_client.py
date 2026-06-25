import csv
import io
import requests
from typing import List, Dict, Any

class FIRMSClient:
    """Client for fetching active fire data from the NASA FIRMS API."""
    
    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api"
    
    def __init__(self, map_key: str):
        if not map_key:
            raise ValueError("NASA FIRMS Map Key must be provided.")
        self.map_key = map_key
        
    def fetch_active_fires(self, country: str, source: str, days: int = 1) -> List[Dict[str, Any]]:
        """
        Fetches active fire data for a specific country, data source, and time range in days.
        Returns a list of dictionaries, where each dictionary represents a fire spot.
        """
        # API URL format: https://firms.modaps.eosdis.nasa.gov/api/country/csv/{MAP_KEY}/{SOURCE}/{COUNTRY_CODE}/{DAYS}
        url = f"{self.BASE_URL}/country/csv/{self.map_key}/{source}/{country}/{days}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from NASA FIRMS API: {e}")
            raise ConnectionError(f"Failed to fetch data from FIRMS API: {e}")
            
        # Parse CSV response
        try:
            csv_file = io.StringIO(response.text)
            reader = csv.DictReader(csv_file)
            fires = []
            for row in reader:
                processed_row = dict(row)
                # Parse numeric fields safely
                if "latitude" in processed_row:
                    processed_row["latitude"] = float(processed_row["latitude"])
                if "longitude" in processed_row:
                    processed_row["longitude"] = float(processed_row["longitude"])
                if "frp" in processed_row:
                    processed_row["frp"] = float(processed_row["frp"])
                fires.append(processed_row)
            return fires
        except Exception as e:
            print(f"Error parsing CSV response from NASA FIRMS API: {e}")
            raise ValueError(f"Failed to parse FIRMS API response: {e}")
