import httpx
import json

API_URL = "http://localhost:8000/api/v1/ingest"
VALID_KEY = "guardx-secret-key-123"

def test_layer3_finetuning():
    print("--- Testing Layer 3 Fine-Tuning (Hardware-Aligned) ---")
    
    # 1. Test Without API Key
    r = httpx.post(API_URL, json={"vibration_rms": 0.08, "temperature": 32.0, "cutting_force": 8.0})
    print(f"\n1. No API Key -> Status: {r.status_code}")
    print(r.json())
    assert r.status_code in (401, 403), "Should be 401/403 without API key"

    # 2. Test With Invalid API Key
    headers = {"X-API-Key": "wrong-key"}
    r = httpx.post(API_URL, headers=headers, json={"vibration_rms": 0.08, "temperature": 32.0, "cutting_force": 8.0})
    print(f"\n2. Invalid API Key -> Status: {r.status_code}")
    print(r.json())
    assert r.status_code == 403, "Should be 403 Forbidden"

    # 3. Test With Valid Key but Physical Bounds Error
    headers = {"X-API-Key": VALID_KEY}
    invalid_data = {
        "machine_id": "CNC-01",
        "sensor_id": "MAIN-01",
        "vibration_rms": 50.0,       # Invalid: > 2.0
        "temperature": 500.0,         # Invalid: > 120
        "cutting_force": -5.0,        # Invalid: < 0
        "motor_current": 0.5,
        "speed_command_level": 65.0,
    }
    r = httpx.post(API_URL, headers=headers, json=invalid_data)
    print(f"\n3. Physical Bounds Validation -> Status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
    assert r.status_code == 422, "Should be 422 Unprocessable Entity"
    detail = r.json()["detail"]
    # Pydantic catches extreme out-of-range values as a list of validation errors
    assert isinstance(detail, list) or "reasons" in detail, "Should contain validation errors"

    # 4. Test Valid Data with new sensor fields
    valid_data = {
        "machine_id": "CNC-01",
        "sensor_id": "MAIN-01",
        "vibration_rms": 0.08,
        "temperature": 32.0,
        "cutting_force": 8.0,
        "motor_current": 0.5,
        "speed_command_level": 65.0,
    }
    r = httpx.post(API_URL, headers=headers, json=valid_data)
    print(f"\n4. Valid Ingestion -> Status: {r.status_code}")
    print(r.json())
    assert r.status_code == 200, "Should be 200 OK"

    print("\n[OK] All Layer 3 fine-tuning tests passed successfully!")

if __name__ == "__main__":
    test_layer3_finetuning()
