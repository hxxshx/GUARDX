"""
GuardX — Ingestion Router (Layer 3)

Hardware-Aligned: Receives 5 raw sensor fields from ESP32.
POST /api/v1/ingest — single sensor reading
POST /api/v1/ingest/batch — batch readings
GET  /api/v1/ingest/latest — latest N readings
"""

from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from datetime import datetime
from api.schemas import SensorReading, BatchReadings, IngestResponse, BatchIngestResponse
from database import crud
from config import SENSOR_RANGES
import os

API_KEY = os.getenv("GUARDX_API_KEY", "guardx-secret-key-123")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion"])


@router.post("", response_model=IngestResponse)
async def ingest_reading(reading: SensorReading, api_key: str = Depends(verify_api_key)):
    """Receive a single sensor reading from ESP32 / simulator."""
    _validate_reading(reading)

    ts = reading.timestamp or datetime.now().isoformat()
    row_id = crud.insert_raw_reading(
        vibration_rms=reading.vibration_rms,
        temperature=reading.temperature,
        cutting_force=reading.cutting_force,
        motor_current=reading.motor_current,
        speed_command_level=reading.speed_command_level,
        timestamp=ts,
        machine_id=reading.machine_id,
        sensor_id=reading.sensor_id,
    )
    return IngestResponse(id=row_id, timestamp=ts)


@router.post("/batch", response_model=BatchIngestResponse)
async def ingest_batch(batch: BatchReadings, api_key: str = Depends(verify_api_key)):
    """Receive multiple sensor readings at once."""
    readings = []
    for r in batch.readings:
        readings.append({
            "vibration_rms": r.vibration_rms,
            "temperature": r.temperature,
            "cutting_force": r.cutting_force,
            "motor_current": r.motor_current,
            "speed_command_level": r.speed_command_level,
            "machine_id": r.machine_id,
            "sensor_id": r.sensor_id,
            "timestamp": r.timestamp or datetime.now().isoformat(),
        })
    count = crud.insert_raw_batch(readings)
    return BatchIngestResponse(count=count)


@router.get("/latest")
async def get_latest(n: int = 60):
    """Get latest N raw sensor readings."""
    return crud.get_latest_raw(n)


@router.get("/count")
async def get_count():
    """Get total count of raw readings."""
    return {"count": crud.get_raw_count()}


def _validate_reading(reading: SensorReading):
    """Additional validation beyond Pydantic with enhanced error context."""
    errors = []
    # Validate raw sensor fields against physical ranges
    sensor_fields = {
        "vibration_rms": reading.vibration_rms,
        "temperature": reading.temperature,
        "cutting_force": reading.cutting_force,
        "motor_current": reading.motor_current,
        "speed_command_level": reading.speed_command_level,
    }
    for sensor, val in sensor_fields.items():
        if sensor in SENSOR_RANGES:
            r = SENSOR_RANGES[sensor]
            if val < r["min"] or val > r["max"]:
                errors.append(f"{sensor} value {val} is outside physical bounds [{r['min']}, {r['max']}]")
            
    if errors:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Sensor Validation Failed",
                "machine_id": reading.machine_id,
                "sensor_id": reading.sensor_id,
                "reasons": errors,
                "action": "Check sensor calibration or physical connection"
            }
        )
