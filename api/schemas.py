"""
GuardX — API Pydantic Schemas

Hardware-Aligned request/response models for all API endpoints.
Sensor fields match demo hardware: ESP32 + MPU6050 + DS18B20 + HX711 + ACS712 + PWM Motor
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─── Ingestion ───────────────────────────────────────────────────

class SensorReading(BaseModel):
    machine_id: str = Field("CNC-01", description="Identifier for the machine")
    sensor_id: str = Field("MAIN-01", description="Identifier for the sensor node")
    vibration_rms: float = Field(..., ge=0, le=2.0, description="Vibration RMS in g (MPU6050)")
    temperature: float = Field(..., ge=10, le=120, description="Temperature in °C (DS18B20)")
    cutting_force: float = Field(..., ge=0, le=50, description="Force in N (HX711 + Load Cell)")
    motor_current: float = Field(0.5, ge=0, le=5.0, description="Current in A (ACS712, optional)")
    speed_command_level: float = Field(65.0, ge=0, le=100, description="PWM duty cycle % (ESP32)")
    timestamp: Optional[str] = None


class BatchReadings(BaseModel):
    readings: list[SensorReading]


class IngestResponse(BaseModel):
    status: str = "ok"
    id: int
    timestamp: str


class BatchIngestResponse(BaseModel):
    status: str = "ok"
    count: int


# ─── Anomaly ─────────────────────────────────────────────────────

class AnomalyResult(BaseModel):
    timestamp: str
    anomaly_score: float
    is_anomaly: bool
    model_type: str = "isolation_forest"
    fault_prediction: Optional[str] = None
    fault_probability: Optional[float] = None


# ─── Health ──────────────────────────────────────────────────────

class HealthScore(BaseModel):
    timestamp: str
    health_score: float
    risk_level: str
    anomaly_risk: float = 0
    vibration_risk: float = 0
    temperature_risk: float = 0
    force_risk: float = 0


# ─── Fault Labels ────────────────────────────────────────────────

class FaultLabelCreate(BaseModel):
    start_timestamp: str
    end_timestamp: str
    fault_type: str = Field(..., description="bearing_wear, imbalance, overheating, overload, coolant_failure")
    severity: str = "medium"
    notes: str = ""
    labeled_by: str = "operator"


class FaultLabelResponse(BaseModel):
    id: int
    start_timestamp: str
    end_timestamp: str
    fault_type: str
    severity: str
    notes: str
    labeled_by: str


# ─── Alerts ──────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    timestamp: str
    alert_type: str
    severity: str
    message: str
    health_score: Optional[float]
    acknowledged: bool


# ─── ML Status ───────────────────────────────────────────────────

class MLStatus(BaseModel):
    current_phase: str
    phase_description: str
    labeled_count: int
    phase_b_threshold: int
    phase_c_threshold: int
    unsupervised_model_loaded: bool
    supervised_model_loaded: bool
    last_training_time: Optional[str] = None


class RetrainResponse(BaseModel):
    status: str
    message: str
    phase: str


# ─── Analytics ───────────────────────────────────────────────────

class SensorSummary(BaseModel):
    sensor: str
    min: float
    max: float
    mean: float
    std: float
    count: int


class DashboardSummary(BaseModel):
    total_readings: int
    latest_health: Optional[HealthScore] = None
    latest_anomaly: Optional[AnomalyResult] = None
    active_alerts: int
    ml_phase: str
