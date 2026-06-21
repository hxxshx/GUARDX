"""
GuardX — FastAPI Main Application

Entry point for the backend API server.
Serves REST API and static dashboard files.
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Ensure project root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import init_db
from api.routers import ingest, analytics, anomaly, health, labels, alerts, ml
from api.mqtt_listener import start_mqtt_listener

# Scheduler reference
_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    init_db()
    print("[GuardX] Database initialized")

    # Start background scheduler
    global _scheduler
    from services.scheduler import start_scheduler
    _scheduler = start_scheduler()
    print("[GuardX] Background scheduler started")

    # Start MQTT Listener
    start_mqtt_listener()
    print("[GuardX] MQTT listener started")

    yield

    # Shutdown
    if _scheduler:
        _scheduler.shutdown(wait=False)
        print("[GuardX] Scheduler stopped")


app = FastAPI(
    title="GuardX",
    description="Predictive Maintenance System for CNC Machines",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(ingest.router)
app.include_router(analytics.router)
app.include_router(anomaly.router)
app.include_router(health.router)
app.include_router(labels.router)
app.include_router(alerts.router)
app.include_router(ml.router)

# Serve dashboard static files
dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
if os.path.exists(dashboard_dir):
    app.mount("/static", StaticFiles(directory=dashboard_dir), name="static")


@app.get("/")
async def serve_dashboard():
    """Serve the main dashboard HTML."""
    index_path = os.path.join(dashboard_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "GuardX API is running. Dashboard not found."}


@app.get("/api/v1/dashboard/summary")
async def dashboard_summary():
    """Aggregated summary for dashboard home."""
    from database import crud
    from ml.engine import get_engine

    engine = get_engine()
    latest_health = crud.get_latest_health(1)
    latest_anomaly = crud.get_latest_anomaly(1)
    active_alerts = crud.get_alerts(acknowledged=False, limit=100)

    return {
        "total_readings": crud.get_raw_count(),
        "latest_health": latest_health[-1] if latest_health else None,
        "latest_anomaly": latest_anomaly[-1] if latest_anomaly else None,
        "active_alerts_count": len(active_alerts),
        "ml_phase": engine.current_phase,
        "ml_phase_description": engine.phase_description,
    }


if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=True)
