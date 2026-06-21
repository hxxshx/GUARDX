"""
GuardX — Fault Labels Router
POST /api/v1/labels — submit a fault label
GET  /api/v1/labels — list labels
GET  /api/v1/labels/count — count labeled events
"""

from fastapi import APIRouter, Query
from api.schemas import FaultLabelCreate
from database import crud

router = APIRouter(prefix="/api/v1/labels", tags=["Labels"])


@router.post("")
async def create_label(label: FaultLabelCreate):
    """Submit a fault label for a time range."""
    row_id = crud.insert_fault_label(
        start_timestamp=label.start_timestamp,
        end_timestamp=label.end_timestamp,
        fault_type=label.fault_type,
        severity=label.severity,
        notes=label.notes,
        labeled_by=label.labeled_by,
    )
    return {"status": "ok", "id": row_id}


@router.get("")
async def get_labels(limit: int = Query(100, ge=1, le=1000)):
    """Get all fault labels."""
    return crud.get_fault_labels(limit)


@router.get("/count")
async def get_label_count():
    """Count labeled events (used for ML phase transition)."""
    count = crud.get_label_count()
    return {"count": count}
