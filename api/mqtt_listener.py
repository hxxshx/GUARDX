"""
GuardX — MQTT Telemetry Listener (Layer 3)

Hardware-Aligned: Receives 5 raw sensor fields from ESP32 via MQTT.
Subscribes to 'guardx/sensors/#' via an MQTT broker.

Expected JSON payload from ESP32:
{
  "timestamp": "...",
  "vibration_rms": 0.08,
  "temperature": 32.5,
  "cutting_force": 8.0,
  "motor_current": 0.5,
  "speed_command_level": 65.0
}
"""

import json
import os
import paho.mqtt.client as mqtt
from datetime import datetime
from typing import Optional
from config import SENSOR_RANGES
from database import crud

MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "guardx/sensors/#")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] Connected to broker {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"[MQTT] Subscribed to {MQTT_TOPIC}")
    else:
        print(f"[MQTT] Failed to connect, return code {rc}")


def on_message(client, userdata, msg):
    """Callback when a telemetry message is received from ESP32."""
    try:
        # Expected topic format: guardx/sensors/{machine_id}/{sensor_id}
        parts = msg.topic.split("/")
        machine_id = parts[2] if len(parts) > 2 else "UNKNOWN"
        sensor_id = parts[3] if len(parts) > 3 else "UNKNOWN"

        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)

        # Extract 5 hardware sensor values
        vibration_rms = float(data.get("vibration_rms", 0.08))
        temperature = float(data.get("temperature", 32.0))
        cutting_force = float(data.get("cutting_force", 8.0))
        motor_current = float(data.get("motor_current", 0.5))
        speed_command_level = float(data.get("speed_command_level", 65.0))
        timestamp = data.get("timestamp", datetime.now().isoformat())

        # Validate ranges before inserting (basic sanity check)
        valid = True
        field_map = {
            "vibration_rms": vibration_rms,
            "temperature": temperature,
            "cutting_force": cutting_force,
            "motor_current": motor_current,
            "speed_command_level": speed_command_level,
        }
        for name, val in field_map.items():
            if name in SENSOR_RANGES:
                r = SENSOR_RANGES[name]
                if val < r["min"] or val > r["max"]:
                    print(f"[MQTT] Invalid {name} value {val} from {machine_id}/{sensor_id}")
                    valid = False

        if valid:
            crud.insert_raw_reading(
                vibration_rms=vibration_rms,
                temperature=temperature,
                cutting_force=cutting_force,
                motor_current=motor_current,
                speed_command_level=speed_command_level,
                timestamp=timestamp,
                machine_id=machine_id,
                sensor_id=sensor_id,
            )

    except Exception as e:
        print(f"[MQTT] Error processing message on {msg.topic}: {e}")


def start_mqtt_listener():
    """Start the MQTT client loop in a background thread."""
    client = mqtt.Client(client_id="GuardX-Backend-Service")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"[MQTT] Could not start listener: {e}")
