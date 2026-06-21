from typing import Optional
"""
GuardX — Health Score & Risk Engine (Layer 7)

Converts ML outputs into a single Health Score (0-100):
  Health = 100 - (w1*anomaly + w2*vibration_rms + w3*temperature + w4*force)

Risk levels: Healthy (80-100), Warning (60-80), Critical (40-60), High Risk (<40)
"""

import numpy as np
from datetime import datetime
from config import (
    HEALTH_WEIGHTS, HEALTH_SMOOTHING_WINDOW, HEALTH_VELOCITY_WINDOW,
    RAPID_DEGRADATION_THRESHOLD, DYNAMIC_ANOMALY_WEIGHT, RISK_LEVELS,
    NORMAL_BASELINES, SENSOR_RANGES, ANOMALY_PERSISTENCE_COUNT,
    ALERT_HEALTH_THRESHOLD, ALERT_COOLDOWN_SECONDS,
    HEALTH_INTERVAL,
)
from database import crud


# Rolling buffer for smoothing
_health_buffer: list[float] = []
_degradation_buffer: list[float] = []  # Smoothing buffer for degradation rate
_last_rul: Optional[float] = None         # Previous RUL for clamping

# Stability constants
_MIN_DEGRADATION_SLOPE = 0.5    # Ignore degradation rates below 0.5% (noise floor)
_MAX_RUL_CHANGE_PER_CYCLE = 60  # RUL can't jump more than 60 min between cycles
_DEGRADATION_SMOOTHING = 5      # Rolling average window for degradation rate

def compute_health_score(
    anomaly_score: float,
    vibration_rms: float,
    temperature: float,
    cutting_force: float,
    model_type: str = "isolation_forest",
    fault_probability: Optional[float] = None,
    timestamp: Optional[str] = None,
) -> dict:
    """
    Compute health score from ML anomaly output and raw sensor values using Dynamic Risk Profiling.

    Args:
        anomaly_score: 0-1 anomaly score (1 = most anomalous)
        vibration_rms: Vibration RMS in g (MPU6050)
        temperature: Temperature in °C (DS18B20)
        cutting_force: Force in N (HX711 + Load Cell)
        model_type: ML phase type
        fault_probability: Confidence of the XGBoost classifier
        timestamp: optional timestamp

    Returns:
        Dict with health_score, risk_level, component risks
    """
    global _health_buffer
    ts = timestamp or datetime.now().isoformat()

    # Compute component risks (0-100 scale)
    anomaly_risk = anomaly_score * 100

    # Vibration risk: how far from normal baseline
    vib_normal = NORMAL_BASELINES["vibration_rms"]["mean"]
    vib_max = SENSOR_RANGES["vibration_rms"]["max"]
    vibration_risk = min(100, max(0, (abs(vibration_rms - vib_normal) / (vib_max - vib_normal)) * 100))

    # Temperature risk: how far from normal baseline  
    temp_normal = NORMAL_BASELINES["temperature"]["mean"]
    temp_max = SENSOR_RANGES["temperature"]["max"]
    temperature_risk = min(100, max(0, ((temperature - temp_normal) / (temp_max - temp_normal)) * 100))

    # Force risk (replaces current_risk — force is primary overload indicator on demo hardware)
    force_normal = NORMAL_BASELINES["cutting_force"]["mean"]
    force_max = SENSOR_RANGES["cutting_force"]["max"]
    force_risk = min(100, max(0, (abs(cutting_force - force_normal) / (force_max - force_normal)) * 100))

    # Dynamic Weight Adjustment
    # If ML is highly confident in Supervised Mode (Phase C), trust the AI and boost anomaly weight
    w_anomaly = HEALTH_WEIGHTS["anomaly"]
    w_vib = HEALTH_WEIGHTS["vibration_rms"]
    w_temp = HEALTH_WEIGHTS["temperature"]
    w_force = HEALTH_WEIGHTS["force"]

    if model_type == "hybrid_phase_c" and fault_probability and fault_probability > 0.85:
        w_anomaly = DYNAMIC_ANOMALY_WEIGHT
        # Dynamically scale down physical sensors proportionately
        remaining_weight = 1.0 - w_anomaly
        orig_sensor_total = w_vib + w_temp + w_force
        if orig_sensor_total > 0:
            w_vib = (w_vib / orig_sensor_total) * remaining_weight
            w_temp = (w_temp / orig_sensor_total) * remaining_weight
            w_force = (w_force / orig_sensor_total) * remaining_weight

    # Weighted health score
    raw_risk = (
        w_anomaly * anomaly_risk +
        w_vib * vibration_risk +
        w_temp * temperature_risk +
        w_force * force_risk
    )
    raw_health = max(0, min(100, 100 - raw_risk))

    # Rolling average smoothing
    _health_buffer.append(raw_health)
    if len(_health_buffer) > HEALTH_SMOOTHING_WINDOW:
        _health_buffer = _health_buffer[-HEALTH_SMOOTHING_WINDOW:]
    
    smoothed_health = round(float(np.mean(_health_buffer)), 2)

    # ──── HARDENED DEGRADATION + RUL PIPELINE ────
    # Problem: Raw single-point rate is noise-sensitive → RUL oscillates.
    # Solution: 3-layer stability: Smoothed Rate → Noise Floor → RUL Clamping.
    
    global _degradation_buffer, _last_rul

    # Step 1: Compute RAW instantaneous degradation rate
    raw_degradation = 0.0
    if len(_health_buffer) >= HEALTH_VELOCITY_WINDOW:
        past_health = _health_buffer[-HEALTH_VELOCITY_WINDOW]
        raw_degradation = float(past_health - smoothed_health)

    # Step 2: Smooth the degradation rate itself (rolling average of rates)
    # This prevents a single noisy anomaly spike from making RUL jump wildly.
    _degradation_buffer.append(raw_degradation)
    if len(_degradation_buffer) > _DEGRADATION_SMOOTHING:
        _degradation_buffer = _degradation_buffer[-_DEGRADATION_SMOOTHING:]
    
    smoothed_degradation = round(float(np.mean(_degradation_buffer)), 2)

    # Step 3: Apply noise floor — ignore micro-fluctuations below threshold
    # If the rate is below 0.5%, it's sensor noise, not real degradation.
    if abs(smoothed_degradation) < _MIN_DEGRADATION_SLOPE:
        effective_degradation = 0.0
    else:
        effective_degradation = smoothed_degradation

    degradation_rate = effective_degradation

    # Risk level classification
    risk_level = classify_risk(smoothed_health)

    # ──── RUL ESTIMATION WITH CLAMPING ────
    # Step 4: Compute RUL only if machine is actively degrading
    rul_minutes = None
    if effective_degradation > 0:
        remaining_health = smoothed_health - ALERT_HEALTH_THRESHOLD
        if remaining_health > 0:
            cycles_to_failure = remaining_health / effective_degradation
            rul_raw = round((cycles_to_failure * HEALTH_INTERVAL) / 60, 1)
            
            # Step 5: Clamp RUL — prevent jumps > 60 min between consecutive readings
            # This ensures the countdown moves smoothly, not erratically.
            if _last_rul is not None and _last_rul > 0:
                max_change = _MAX_RUL_CHANGE_PER_CYCLE
                clamped = max(_last_rul - max_change, min(_last_rul + max_change, rul_raw))
                rul_minutes = max(0, round(clamped, 1))
            else:
                rul_minutes = max(0, rul_raw)
        else:
            rul_minutes = 0.0  # Already below threshold
    elif effective_degradation < 0:
        # Machine is RECOVERING (health going up) — signal stability
        rul_minutes = None  # No failure projected
    else:
        # Zero effective slope — machine is stable
        rul_minutes = None
    
    _last_rul = rul_minutes

    # DB-compatible fields only (these columns exist in the health_scores table)
    db_result = {
        "timestamp": ts,
        "health_score": smoothed_health,
        "risk_level": risk_level,
        "anomaly_risk": round(anomaly_risk, 2),
        "vibration_risk": round(vibration_risk, 2),
        "temperature_risk": round(temperature_risk, 2),
        "force_risk": round(force_risk, 2),
    }

    # Store in database
    crud.insert_health_score(**db_result)

    # Full result for API (includes RUL + degradation for Dashboard)
    result = {
        **db_result,
        "degradation_rate": degradation_rate,
        "rul_minutes": rul_minutes,
    }

    # Check if alert needed (Absolute drop OR Velocity drop)
    _check_alert(smoothed_health, risk_level, degradation_rate, ts)

    return result


def classify_risk(health_score: float) -> str:
    """Classify health score into risk level."""
    for level, (low, high) in RISK_LEVELS.items():
        if low <= health_score <= high:
            return level
    return "high_risk"


def _check_alert(health_score: float, risk_level: str, degradation_rate: float, timestamp: str):
    """Generate alert if health is below threshold OR degrading too fast."""
    is_absolute_alert = health_score < ALERT_HEALTH_THRESHOLD
    is_velocity_alert = degradation_rate >= RAPID_DEGRADATION_THRESHOLD

    if not is_absolute_alert and not is_velocity_alert:
        return

    # Check persistence: only alert if consecutive anomalies
    consecutive = crud.get_consecutive_anomalies(ANOMALY_PERSISTENCE_COUNT)
    if consecutive < ANOMALY_PERSISTENCE_COUNT and not is_velocity_alert:
        # Velocity alerts bypass the anomaly persistence check because rapid drops are critical
        return

    # Check cooldown
    last_alert = crud.get_latest_alert_time()
    if last_alert:
        from datetime import datetime as dt
        try:
            last_dt = dt.fromisoformat(last_alert)
            now_dt = dt.fromisoformat(timestamp)
            diff = (now_dt - last_dt).total_seconds()
            if diff < ALERT_COOLDOWN_SECONDS:
                return
        except (ValueError, TypeError):
            pass

    # Generate alert
    if is_velocity_alert and not is_absolute_alert:
        severity = "high"
        message = (
            f"Rapid degradation detected! Health dropped {degradation_rate}% "
            f"in {HEALTH_VELOCITY_WINDOW} cycles. Current Health: {health_score:.1f}%."
        )
        alert_type = "velocity_warning"
    else:
        severity = "critical" if health_score < 40 else "warning"
        message = (
            f"Machine health at {health_score:.1f}% ({risk_level}). "
            f"Immediate attention recommended."
        )
        alert_type = "health_degradation"
        
    crud.insert_alert(
        timestamp=timestamp,
        alert_type=alert_type,
        severity=severity,
        message=message,
        health_score=health_score,
    )

    # Dispatch to external systems (Layer 8 Hook)
    from services.notifier import trigger_alert
    trigger_alert(alert_type, severity, message, health_score)


def compute_batch_health(
    anomaly_results: list[dict],
    sensor_data: list[dict],
) -> list[dict]:
    """
    Compute health scores for a batch of readings.

    Args:
        anomaly_results: list of dicts with anomaly_score
        sensor_data: list of dicts with vibration, temperature, current, timestamp
    """
    results = []
    for ar, sd in zip(anomaly_results, sensor_data):
        result = compute_health_score(
            anomaly_score=ar.get("anomaly_score", 0),
            vibration_rms=sd.get("vibration_rms", 0.08),
            temperature=sd.get("temperature", 32.0),
            cutting_force=sd.get("cutting_force", 8.0),
            model_type=ar.get("model_type", "isolation_forest"),
            fault_probability=ar.get("fault_probability"),
            timestamp=sd.get("timestamp"),
        )
        results.append(result)
    return results
