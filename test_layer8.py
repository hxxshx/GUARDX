import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from services.notifier import trigger_alert

def test_layer8_notifications():
    print("--- Testing Layer 8 (Enterprise Notifier) ---")
    
    # Simulate a critical health degradation that would normally come from the DB/Health Engine
    alert_type = "health_degradation"
    severity = "critical"
    message = "Machine health at 38.4% (high_risk). Immediate attention recommended."
    health_score = 38.4
    
    print(f"\n[TEST] Simulating CRITICAL Alert Dispatch...")
    trigger_alert(alert_type, severity, message, health_score)

if __name__ == "__main__":
    test_layer8_notifications()
