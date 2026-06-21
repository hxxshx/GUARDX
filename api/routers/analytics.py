"""
GuardX — Analytics Router
GET /api/v1/analytics/sensor/{name} — sensor history
GET /api/v1/analytics/summary — statistical summary
"""

from fastapi import APIRouter, Query
from database import crud
import numpy as np

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


VALID_SENSORS = ["vibration_rms", "temperature", "cutting_force", "motor_current", "speed_command_level"]


@router.get("/sensor/{sensor_name}")
async def get_sensor_data(sensor_name: str, n: int = Query(60, ge=1, le=5000)):
    """Get latest N readings for a specific sensor."""
    readings = crud.get_latest_raw(n)
    if sensor_name not in VALID_SENSORS:
        return {"error": f"Unknown sensor: {sensor_name}. Valid: {VALID_SENSORS}"}
    
    return {
        "sensor": sensor_name,
        "data": [
            {"timestamp": r["timestamp"], "value": r.get(sensor_name, 0)}
            for r in readings
        ],
        "count": len(readings),
    }


@router.get("/summary")
async def get_summary():
    """Statistical summary of recent sensor data."""
    readings = crud.get_latest_raw(500)
    if not readings:
        return {"status": "no_data"}
    
    result = {}
    for sensor in VALID_SENSORS:
        values = [r.get(sensor, 0) for r in readings]
        if not values:
            continue
        result[sensor] = {
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "mean": round(float(np.mean(values)), 4),
            "std": round(float(np.std(values)), 4),
            "count": len(values),
        }
    return result


@router.get("/features/latest")
async def get_latest_features(n: int = Query(60, ge=1, le=1000)):
    """Get latest processed features."""
    return crud.get_latest_features(n)
