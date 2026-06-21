from typing import Optional
"""
GuardX — Anomaly Router
GET /api/v1/anomaly/latest — latest anomaly result
GET /api/v1/anomaly/history — anomaly history
"""

from fastapi import APIRouter, Query
from database import crud

router = APIRouter(prefix="/api/v1/anomaly", tags=["Anomaly"])


@router.get("/latest")
async def get_latest_anomaly(n: int = Query(1, ge=1, le=100)):
    """Get latest N anomaly results."""
    results = crud.get_latest_anomaly(n)
    return results


@router.get("/history")
async def get_anomaly_history(
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(500, ge=1, le=5000),
):
    """Get anomaly detection history."""
    return crud.get_anomaly_history(start, end, limit)
