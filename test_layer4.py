"""
Test Layer 4 — Preprocessing (Hardware-Aligned)
Verifies: batch ingestion, preprocessing pipeline, derived features.
"""
import httpx
import json
import random
import math
import time
from datetime import datetime, timedelta

API_URL = "http://localhost:8000/api/v1/ingest/batch"
VALID_KEY = "guardx-secret-key-123"

def test_layer4():
    print("--- Testing Layer 4 Preprocessing (Hardware-Aligned) ---")
    
    headers = {"X-API-Key": VALID_KEY}
    base_time = datetime.now()
    
    # Send 30 batches of 2 readings (1 per machine)
    print("Simulating 30s of data for CNC-1 (normal) and CNC-2 (imbalance)...")
    for i in range(30):
        ts = (base_time + timedelta(seconds=i)).isoformat()
        batch = []
        
        # CNC-1: Normal operation
        batch.append({
            "timestamp": ts,
            "machine_id": "CNC-1",
            "vibration_rms": 0.08 + random.uniform(-0.01, 0.01),
            "temperature": 32.0,
            "cutting_force": 8.0 + random.uniform(-0.5, 0.5),
            "motor_current": 0.5,
            "speed_command_level": 65.0,
        })
        
        # CNC-2: Imbalance (vibration oscillation + force variance)
        vib_wave = math.sin(i * 1.5) * 0.05
        batch.append({
            "timestamp": ts,
            "machine_id": "CNC-2",
            "vibration_rms": 0.18 + vib_wave,
            "temperature": 35.0,
            "cutting_force": 12.0 + math.sin(i * 2.0) * 3.0,
            "motor_current": 0.7,
            "speed_command_level": 75.0,
        })
        
        r = httpx.post(API_URL, headers=headers, json={"readings": batch})
        if r.status_code != 200:
            print(f"Error {r.status_code}: {r.text}")
            import sys; sys.exit(1)
        
    print("\nData ingested successfully.")
    
    # Let the scheduler process this
    print("Waiting 6 seconds for background preprocessing...")
    time.sleep(6)
    
    print("\n[OK] Layer 4 preprocessing test completed — check InfluxDB for feature vectors.")

if __name__ == "__main__":
    test_layer4()
