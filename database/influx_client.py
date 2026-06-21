"""
GuardX - InfluxDB Client Manager (Layer 5)

Hardware-Aligned: Stores 5 raw sensor fields + 7 feature vector fields.
"""
import os
import certifi
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Ensure environment variables are loaded
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# InfluxDB Configuration
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "guardx-org")
INFLUX_BUCKET_RAW = os.getenv("INFLUX_BUCKET_RAW", "guardx_raw")
INFLUX_BUCKET_FEATURES = os.getenv("INFLUX_BUCKET_FEATURES", "guardx_features")

# Global client instance
_client = None
_write_api = None
_query_api = None

def get_influx_client():
    """Initializes and returns the global InfluxDB client and APIs."""
    global _client, _write_api, _query_api
    if _client is None:
        try:
            _client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, ssl_ca_cert=certifi.where())
            _write_api = _client.write_api(write_options=SYNCHRONOUS)
            _query_api = _client.query_api()
        except Exception as e:
            print(f"Failed to connect to InfluxDB: {e}")
            _client = None
            
    return _client, _write_api, _query_api

def close_influx_client():
    """Closes the global InfluxDB client."""
    global _client, _write_api, _query_api
    if _client:
        _client.close()
        _client = None
        _write_api = None
        _query_api = None

def write_raw_reading(vibration_rms: float, temperature: float, cutting_force: float,
                      motor_current: float, speed_command_level: float,
                      timestamp: str, machine_id: str, sensor_id: str):
    """Write a single raw reading to InfluxDB (5 hardware sensor fields)."""
    _, write_api, _ = get_influx_client()
    if not write_api: return False
    
    point = Point("sensor_reading") \
        .tag("machine_id", machine_id) \
        .tag("sensor_id", sensor_id) \
        .field("vibration_rms", float(vibration_rms)) \
        .field("temperature", float(temperature)) \
        .field("cutting_force", float(cutting_force)) \
        .field("motor_current", float(motor_current)) \
        .field("speed_command_level", float(speed_command_level)) \
        .time(timestamp, WritePrecision.NS)
        
    try:
        write_api.write(bucket=INFLUX_BUCKET_RAW, org=INFLUX_ORG, record=point)
        return True
    except Exception as e:
        print(f"InfluxDB write error: {e}")
        return False

def write_raw_batch(readings: list[dict]):
    """Write a batch of raw readings to InfluxDB."""
    _, write_api, _ = get_influx_client()
    if not write_api: return False
    
    points = []
    for r in readings:
        p = Point("sensor_reading") \
            .tag("machine_id", r.get("machine_id", "CNC-01")) \
            .tag("sensor_id", r.get("sensor_id", "MAIN-01")) \
            .field("vibration_rms", float(r["vibration_rms"])) \
            .field("temperature", float(r["temperature"])) \
            .field("cutting_force", float(r["cutting_force"])) \
            .field("motor_current", float(r.get("motor_current", 0.5))) \
            .field("speed_command_level", float(r.get("speed_command_level", 65.0))) \
            .time(r["timestamp"], WritePrecision.NS)
        points.append(p)
        
    try:
        write_api.write(bucket=INFLUX_BUCKET_RAW, org=INFLUX_ORG, record=points)
        return True
    except Exception as e:
        print(f"InfluxDB batch write error: {e}")
        return False

def write_processed_features(features: list[dict]):
    """Write processed feature vectors to InfluxDB (7 ML features)."""
    _, write_api, _ = get_influx_client()
    if not write_api: return False
    
    points = []
    for f in features:
        p = Point("feature_vector") \
            .tag("machine_id", f.get("machine_id", "CNC-01")) \
            .tag("sensor_id", f.get("sensor_id", "MAIN-01")) \
            .field("vibration_rms", float(f.get("vibration_rms", 0))) \
            .field("temperature", float(f.get("temperature", 0))) \
            .field("temperature_rate", float(f.get("temperature_rate", 0))) \
            .field("cutting_force", float(f.get("cutting_force", 0))) \
            .field("force_variance", float(f.get("force_variance", 0))) \
            .field("motor_current", float(f.get("motor_current", 0))) \
            .field("speed_command_level", float(f.get("speed_command_level", 0))) \
            .time(f["timestamp"], WritePrecision.NS)
        points.append(p)
        
    try:
        write_api.write(bucket=INFLUX_BUCKET_FEATURES, org=INFLUX_ORG, record=points)
        return True
    except Exception as e:
        print(f"InfluxDB feature write error: {e}")
        return False
