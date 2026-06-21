"""
Test Layer 7 — Health Score & Risk Engine (Hardware-Aligned)
Verifies: health calculation with new sensor parameters, dynamic weighting, velocity alerts.
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from services.health_engine import compute_health_score
from config import HEALTH_WEIGHTS, DYNAMIC_ANOMALY_WEIGHT

def test_layer7():
    print("--- Testing Layer 7 (Hardware-Aligned Health & Risk Engine) ---")

    # 1. Test Static Calculation (Normal)
    print("\n[1] Testing Static ML Calculation...")
    res_normal = compute_health_score(
        anomaly_score=0.1,           # Low anomaly
        vibration_rms=0.08,          # Normal for MPU6050
        temperature=32.0,            # Normal for DS18B20
        cutting_force=8.0,           # Normal for load cell
        model_type="isolation_forest",
        fault_probability=None
    )
    print(f"  Normal State Health: {res_normal['health_score']}% ({res_normal['risk_level']})")

    # 2. Test Dynamic Weighting (Phase C, High Confidence)
    print("\n[2] Testing Dynamic ML Weighting (Phase C > 85% Confidence)...")
    res_dynamic = compute_health_score(
        anomaly_score=0.95,
        vibration_rms=0.12,          # Slightly elevated
        temperature=38.0,
        cutting_force=12.0,
        model_type="hybrid_phase_c",
        fault_probability=0.92       # High confidence triggers override
    )
    print(f"  Dynamic Weight Health: {res_dynamic['health_score']}% ({res_dynamic['risk_level']})")
    print(f"  (ML weight dynamically overridden to {DYNAMIC_ANOMALY_WEIGHT*100}%)")

    # 3. Test Health Velocity (Rapid Degradation)
    print("\n[3] Testing Health Velocity (Degradation Tracking)...")
    print("  Simulating a rapid health drop across 5 readings...")
    
    for i in range(4):
        compute_health_score(
            anomaly_score=0.2 + (i * 0.1),
            vibration_rms=0.10 + i * 0.03,
            temperature=34 + i * 3,
            cutting_force=10.0 + i * 2.0,
        )
    
    # Reading 5: HUGE spike
    res_spike = compute_health_score(
        anomaly_score=0.99,
        vibration_rms=0.25,          # Critical vibration
        temperature=65.0,            # Critical temperature
        cutting_force=30.0,          # Critical force
    )
    print(f"  After Spike Health: {res_spike['health_score']}% ({res_spike['risk_level']})")
    print("  Check database logs or alerts for 'velocity_warning'!")

if __name__ == "__main__":
    test_layer7()
