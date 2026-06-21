"""
GuardX — Preprocessing & Feature Engineering (Layer 4)

Hardware-Aligned for Demo Setup:
  ESP32 + MPU6050 + DS18B20 + HX711 + Load Cell + ACS712 + PWM Motor

Converts raw sensor values into ML-ready 7-feature vectors:
  vibration_rms, temperature, temperature_rate, cutting_force,
  force_variance, motor_current, speed_command_level

Feature Symmetry Contract:
  - temperature_rate = temperature.diff().fillna(0)
  - force_variance = cutting_force.rolling(ROLLING_WINDOW, min_periods=1).var().fillna(0)
  - ROLLING_WINDOW must match config.py and simulator.py (currently 10)
  - NaN handling: first diff = 0, first rolling var = 0
"""

import numpy as np
import pandas as pd
from config import SMOOTHING_WINDOW, ROLLING_WINDOW, OUTLIER_IQR_MULTIPLIER


# ─── Feature Vector Definition ───────────────────────────────────
# STRICT ORDER — Must match simulator CSV_COLUMNS and classifier training order.
# Changing this order will silently corrupt the ML model.

def get_feature_vector_columns() -> list[str]:
    """Return the exact list of feature columns used for ML input."""
    return [
        "vibration_rms",
        "temperature",
        "temperature_rate",
        "cutting_force",
        "force_variance",
        "motor_current",
        "speed_command_level",
    ]


def features_to_array(features: list[dict]) -> np.ndarray:
    """Convert feature dicts to numpy array for ML input."""
    cols = get_feature_vector_columns()
    return np.array([[f.get(c, 0) for c in cols] for f in features])


# ─── Preprocessing Pipeline ──────────────────────────────────────

# Raw sensor columns expected from hardware/API ingestion
RAW_SENSOR_COLUMNS = [
    "vibration_rms", "temperature", "cutting_force",
    "motor_current", "speed_command_level",
]

# Derived columns computed in this pipeline (feature symmetry)
DERIVED_COLUMNS = ["temperature_rate", "force_variance"]


def preprocess_readings(readings: list[dict]) -> list[dict]:
    """
    Full preprocessing pipeline on a list of raw sensor readings.

    This function computes the SAME derived features as the simulator:
      - temperature_rate = temperature.diff().fillna(0)
      - force_variance = cutting_force.rolling(ROLLING_WINDOW).var().fillna(0)

    Args:
        readings: List of dicts with sensor values + machine_id + timestamp

    Returns:
        List of feature vector dicts ready for ML (7 features)
    """
    if not readings:
        return []

    df = pd.DataFrame(readings)

    # Ensure machine_id exists for grouping
    if "machine_id" not in df.columns:
        df["machine_id"] = "CNC-01"
    if "sensor_id" not in df.columns:
        df["sensor_id"] = "MAIN-01"

    # Cap outliers on raw sensor columns only
    for col in RAW_SENSOR_COLUMNS:
        if col in df.columns:
            df[col] = _cap_outliers(df[col].values)

    results = []

    # Process each machine independently so rolling windows don't mix
    for machine_id, group in df.groupby("machine_id"):
        group = group.sort_values(by="timestamp").copy()

        if len(group) < ROLLING_WINDOW:
            results.extend(_basic_features(group.to_dict(orient="records")))
            continue

        # ─── Smoothing ────────────────────────────────────────
        for col in RAW_SENSOR_COLUMNS:
            if col in group.columns:
                group[f"{col}_smooth"] = group[col].rolling(
                    window=SMOOTHING_WINDOW, min_periods=1
                ).mean()

        # ─── Derived Features (MUST match simulator exactly) ──
        # temperature_rate: identical to simulator's _compute_temperature_rate()
        group["temperature_rate"] = group["temperature"].diff().fillna(0)

        # force_variance: identical to simulator's _compute_force_variance()
        group["force_variance"] = group["cutting_force"].rolling(
            window=ROLLING_WINDOW, min_periods=1
        ).var().fillna(0)

        # ─── Build output feature vectors ─────────────────────
        feature_cols = [
            "timestamp", "machine_id", "sensor_id",
        ] + get_feature_vector_columns()

        # Ensure all columns exist
        for col in feature_cols:
            if col not in group.columns:
                group[col] = 0.0

        results.extend(group[feature_cols].fillna(0).to_dict(orient="records"))

    return results


def _cap_outliers(values: np.ndarray) -> np.ndarray:
    """Cap outliers using IQR method."""
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    lower = q1 - OUTLIER_IQR_MULTIPLIER * iqr
    upper = q3 + OUTLIER_IQR_MULTIPLIER * iqr
    return np.clip(values, lower, upper)


def _basic_features(readings: list[dict]) -> list[dict]:
    """Generate basic features when not enough data for rolling windows."""
    results = []
    prev_temp = None

    for r in readings:
        current_temp = r.get("temperature", 32.0)
        temp_rate = (current_temp - prev_temp) if prev_temp is not None else 0.0
        prev_temp = current_temp

        results.append({
            "timestamp": r.get("timestamp", ""),
            "machine_id": r.get("machine_id", "CNC-01"),
            "sensor_id": r.get("sensor_id", "MAIN-01"),
            "vibration_rms": r.get("vibration_rms", 0.08),
            "temperature": current_temp,
            "temperature_rate": temp_rate,
            "cutting_force": r.get("cutting_force", 8.0),
            "force_variance": 0.0,  # Can't compute rolling var with < ROLLING_WINDOW
            "motor_current": r.get("motor_current", 0.5),
            "speed_command_level": r.get("speed_command_level", 65.0),
        })
    return results
