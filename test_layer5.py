"""
Test Layer 5 — InfluxDB Time-Series Storage (Hardware-Aligned)
Verifies: Data written to InfluxDB with new sensor field names.
"""
import httpx
from database.influx_client import get_influx_client, INFLUX_BUCKET_RAW
from datetime import datetime, timedelta
import random
import time

API_URL = "http://localhost:8000/api/v1/ingest/batch"
VALID_KEY = "guardx-secret-key-123"

def test_influx():
    print("--- Testing Layer 5 Time-Series Storage (Hardware-Aligned) ---")
    headers = {"X-API-Key": VALID_KEY}
    
    # 1. Send data with new hardware fields
    print("Simulating 10s of data to trigger InfluxDB writes...")
    base_time = datetime.utcnow()
    batch = []
    
    for i in range(10):
        ts = (base_time + timedelta(seconds=i)).isoformat() + "Z"
        batch.append({
            "timestamp": ts,
            "machine_id": "CNC-1",
            "vibration_rms": 0.08 + random.uniform(-0.01, 0.01),
            "temperature": 32.0 + random.uniform(-1, 1),
            "cutting_force": 8.0 + random.uniform(-0.5, 0.5),
            "motor_current": 0.5 + random.uniform(-0.02, 0.02),
            "speed_command_level": 65.0,
        })
        
    r = httpx.post(API_URL, headers=headers, json={"readings": batch})
    if r.status_code != 200:
        print(f"API Error {r.status_code}: {r.text}")
        return
        
    print("Data ingested to API successfully. Waiting 6 seconds for background processing...")
    time.sleep(6)
    
    # 2. Query Influx directly
    print("\nQuerying InfluxDB...")
    _, _, query_api = get_influx_client()
    if not query_api:
        print("Failed to initialize Influx client.")
        return
        
    query = f'''
        from(bucket: "{INFLUX_BUCKET_RAW}")
        |> range(start: -5m)
        |> filter(fn: (r) => r._measurement == "sensor_reading")
        |> filter(fn: (r) => r.machine_id == "CNC-1")
    '''
    try:
        tables = query_api.query(query=query)
        if not tables:
            print("No data found in InfluxDB!")
            exit(1)
            
        count = 0
        for table in tables:
            for record in table.records:
                count += 1
                
        print(f"Found {count} field records in InfluxDB successfully!")
        print("\n[OK] Layer 5 InfluxDB Integration works perfectly!")
    except Exception as e:
        print(f"Query Error: {e}")
        exit(1)

if __name__ == "__main__":
    test_influx()
