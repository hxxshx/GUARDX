"""
GuardX — Health Score Router

Hardware-Aligned: Uses demo motor sensor fields for diagnostics.
GET /api/v1/health/current — current health score
GET /api/v1/health/history — health score history
GET /api/v1/health/diagnostics — fault signature diagnosis
"""

from fastapi import APIRouter, Query
from database import crud

router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get("/current")
async def get_current_health():
    """Get the most recent health score."""
    results = crud.get_latest_health(n=1)
    if not results:
        return {"health_score": 100, "risk_level": "healthy", "message": "No data yet"}
    return results[-1]


@router.get("/history")
async def get_health_history(limit: int = Query(500, ge=1, le=5000)):
    """Get health score history."""
    return crud.get_health_history(limit)


@router.get("/diagnostics")
async def get_cnc_diagnostics():
    """
    Demo hardware fault signature diagnosis.

    Runs the domain intelligence engine that maps multi-sensor feature
    patterns to known fault modes (bearing_wear, imbalance, overheating,
    overload, coolant_failure).
    """
    from services.cnc_diagnostics import diagnose_cnc_fault

    # Get latest raw sensor reading
    latest_raw = crud.get_latest_raw(n=1)
    # Get latest processed features
    latest_features = crud.get_features_for_training(limit=1)

    if not latest_raw:
        return {
            "status": "no_data",
            "message": "No sensor data available for diagnosis"
        }

    raw = latest_raw[0] if latest_raw else {}
    feat = latest_features[0] if latest_features else {}

    diagnosis = diagnose_cnc_fault(
        vibration_rms=raw.get("vibration_rms", feat.get("vibration_rms", 0.08)),
        temperature=raw.get("temperature", feat.get("temperature", 32.0)),
        temperature_rate=feat.get("temperature_rate", 0.0),
        cutting_force=raw.get("cutting_force", feat.get("cutting_force", 8.0)),
        force_variance=feat.get("force_variance", 0.0),
        motor_current=raw.get("motor_current", feat.get("motor_current", 0.5)),
        speed_command_level=raw.get("speed_command_level", feat.get("speed_command_level", 65.0)),
    )

    return diagnosis
