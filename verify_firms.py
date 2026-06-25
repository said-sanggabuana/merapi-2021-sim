import os
import sys
import requests
import csv
import io

def main():
    print("=== NASA FIRMS Connection Verification Start ===")
    
    # 1. Load map key from environment
    map_key = os.getenv("NASA_FIRMS_MAP_KEY", "").strip()
    if not map_key:
        print("[ERROR] NASA_FIRMS_MAP_KEY environment variable is missing or empty.")
        print("Please set it in your environment or load it from a .env file.")
        sys.exit(1)
        
    # 2. Configure variables for Mount Merapi National Park
    bbox = "110.34,-7.63,110.52,-7.51"
    source = "VIIRS_SNPP_NRT"
    days = 1
    
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/{bbox}/{days}"
    print(f"[INFO] Querying URL: https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY_HIDDEN]/{source}/{bbox}/{days}")
    
    try:
        response = requests.get(url, timeout=15)
        
        # 3. Evaluate response code
        if response.status_code == 200:
            print("[SUCCESS] Successfully connected to NASA FIRMS API (HTTP 200).")
            
            # Parse text stream CSV values into anomalies summary
            csv_file = io.StringIO(response.text)
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            
            print(f"[INFO] Total active thermal anomalies found in the last 24h: {len(rows)}")
            if len(rows) > 0:
                print("\nActive Anomalies Detail:")
                for i, row in enumerate(rows[:5]):
                    lat = row.get("latitude")
                    lon = row.get("longitude")
                    conf = row.get("confidence")
                    frp = row.get("frp")
                    date = row.get("acq_date")
                    time = row.get("acq_time")
                    print(f"  {i+1}. Lat: {lat}, Lon: {lon} | Conf: {conf} | FRP: {frp} | Date: {date} {time}")
                if len(rows) > 5:
                    print(f"  ... and {len(rows) - 5} more.")
            
        elif response.status_code == 401:
            print(f"[ERROR] Unauthorized (HTTP 401). Your NASA_FIRMS_MAP_KEY may be invalid.")
            sys.exit(1)
        elif response.status_code == 403:
            print(f"[ERROR] Forbidden (HTTP 403). Access is blocked.")
            sys.exit(1)
        else:
            print(f"[ERROR] Server returned response code: {response.status_code}")
            print(f"Response snippet: {response.text[:200]}")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to establish connection to NASA FIRMS server: {e}")
        sys.exit(1)

    print("=== NASA FIRMS Connection Verification End ===")

if __name__ == "__main__":
    main()
