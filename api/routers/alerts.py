from typing import Optional
"""
GuardX — Alerts Router
GET /api/v1/alerts — list alerts
PUT /api/v1/alerts/{id}/acknowledge — acknowledge an alert
"""

from fastapi import APIRouter, Query
from database import crud

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.get("")
async def get_alerts(
    acknowledged: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=1000),
):
    """Get alerts with optional filter."""
    return crud.get_alerts(acknowledged=acknowledged, limit=limit)


@router.get("/active")
async def get_active_alerts():
    """Get unacknowledged alerts."""
    return crud.get_alerts(acknowledged=False, limit=50)


@router.put("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """Acknowledge an alert."""
    crud.acknowledge_alert(alert_id)
    return {"status": "ok", "id": alert_id}
