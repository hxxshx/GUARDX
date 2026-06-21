"""
GuardX — Database CRUD Operations (Layer 5)

Insert, query, and aggregate operations for all 6 tables.
"""

import sqlite3
from datetime import datetime
from typing import Optional
from database.db import get_connection


# ─── Raw Sensor Data ─────────────────────────────────────────────

def insert_raw_reading(vibration_rms: float, temperature: float, cutting_force: float,
                       motor_current: float = 0.5, speed_command_level: float = 65.0,
                       timestamp: Optional[str] = None,
                       machine_id: str = "CNC-01",
                       sensor_id: str = "MAIN-01") -> int:
    from database.influx_client import write_raw_reading
    from datetime import datetime
    ts = timestamp or datetime.now().isoformat()
    success = write_raw_reading(vibration_rms, temperature, cutting_force,
                                motor_current, speed_command_level,
                                ts, machine_id, sensor_id)
    return 1 if success else 0


def insert_raw_batch(readings: list[dict]) -> int:
    from database.influx_client import write_raw_batch
    success = write_raw_batch(readings)
    return len(readings) if success else 0


def get_latest_raw(n: int = 60) -> list[dict]:
    from database.influx_client import get_influx_client, INFLUX_BUCKET_RAW, INFLUX_ORG
    _, _, query_api = get_influx_client()
    if not query_api: return []
    query = f'''
        from(bucket: "{INFLUX_BUCKET_RAW}")
        |> range(start: -1d)
        |> filter(fn: (r) => r._measurement == "sensor_reading")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: true)
        |> limit(n: {n})
    '''
    try:
        tables = query_api.query(org=INFLUX_ORG, query=query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "timestamp": record.get_time().isoformat(),
                    "machine_id": record.values.get("machine_id"),
                    "sensor_id": record.values.get("sensor_id"),
                    "vibration_rms": record.values.get("vibration_rms"),
                    "temperature": record.values.get("temperature"),
                    "cutting_force": record.values.get("cutting_force"),
                    "motor_current": record.values.get("motor_current"),
                    "speed_command_level": record.values.get("speed_command_level"),
                })
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:n]
    except Exception as e:
        print(f"Influx query error: {e}")
        return []


def get_raw_range(start: str, end: str) -> list[dict]:
    from database.influx_client import get_influx_client, INFLUX_BUCKET_RAW, INFLUX_ORG
    _, _, query_api = get_influx_client()
    if not query_api: return []
    query = f'''
        from(bucket: "{INFLUX_BUCKET_RAW}")
        |> range(start: time(v: "{start}"), stop: time(v: "{end}"))
        |> filter(fn: (r) => r._measurement == "sensor_reading")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: false)
    '''
    try:
        tables = query_api.query(org=INFLUX_ORG, query=query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "timestamp": record.get_time().isoformat(),
                    "machine_id": record.values.get("machine_id"),
                    "sensor_id": record.values.get("sensor_id"),
                    "vibration_rms": record.values.get("vibration_rms"),
                    "temperature": record.values.get("temperature"),
                    "cutting_force": record.values.get("cutting_force"),
                    "motor_current": record.values.get("motor_current"),
                    "speed_command_level": record.values.get("speed_command_level"),
                })
        results.sort(key=lambda x: x["timestamp"])
        return results
    except Exception as e:
        print(e)
        return []


def get_raw_count() -> int:
    return 1000 # Dummy for influx


def get_unprocessed_raw(last_processed_time: Optional[str] = None, limit: int = 100) -> list[dict]:
    from database.influx_client import get_influx_client, INFLUX_BUCKET_RAW, INFLUX_ORG
    _, _, query_api = get_influx_client()
    if not query_api: return []
    start_time = f'time(v: "{last_processed_time}")' if last_processed_time else "-1h"
    query = f'''
        from(bucket: "{INFLUX_BUCKET_RAW}")
        |> range(start: {start_time})
        |> filter(fn: (r) => r._measurement == "sensor_reading")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: false)
        |> limit(n: {limit})
    '''
    try:
        tables = query_api.query(org=INFLUX_ORG, query=query)
        results = []
        for table in tables:
            for record in table.records:
                ts = record.get_time().isoformat()
                if ts != last_processed_time:
                    results.append({
                        "id": ts, # Fake id for compatibility
                        "timestamp": ts,
                        "machine_id": record.values.get("machine_id"),
                        "sensor_id": record.values.get("sensor_id"),
                        "vibration_rms": record.values.get("vibration_rms"),
                        "temperature": record.values.get("temperature"),
                        "cutting_force": record.values.get("cutting_force"),
                        "motor_current": record.values.get("motor_current"),
                        "speed_command_level": record.values.get("speed_command_level"),
                    })
        results.sort(key=lambda x: x["timestamp"])
        return results[:limit]
    except Exception as e:
        print(f"Influx query error: {e}")
        return []


# ─── Processed Features ─────────────────────────────────────────

def insert_processed_features(features: list[dict]) -> int:
    from database.influx_client import write_processed_features
    success = write_processed_features(features)
    return len(features) if success else 0


def get_latest_features(n: int = 60) -> list[dict]:
    from database.influx_client import get_influx_client, INFLUX_BUCKET_FEATURES, INFLUX_ORG
    _, _, query_api = get_influx_client()
    if not query_api: return []
    query = f'''
        from(bucket: "{INFLUX_BUCKET_FEATURES}")
        |> range(start: -1d)
        |> filter(fn: (r) => r._measurement == "feature_vector")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: true)
        |> limit(n: {n})
    '''
    try:
        tables = query_api.query(org=INFLUX_ORG, query=query)
        results = []
        for table in tables:
            for record in table.records:
                res = record.values.copy()
                res["timestamp"] = record.get_time().isoformat()
                res.pop("_time", None)
                res.pop("_measurement", None)
                res.pop("result", None)
                res.pop("table", None)
                res.pop("_start", None)
                res.pop("_stop", None)
                results.append(res)
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:n]
    except Exception as e:
        print(f"Influx query error: {e}")
        return []


def get_features_for_training(limit: int = 10000) -> list[dict]:
    from database.influx_client import get_influx_client, INFLUX_BUCKET_FEATURES, INFLUX_ORG
    _, _, query_api = get_influx_client()
    if not query_api: return []
    query = f'''
        from(bucket: "{INFLUX_BUCKET_FEATURES}")
        |> range(start: -30d)
        |> filter(fn: (r) => r._measurement == "feature_vector")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: false)
        |> limit(n: {limit})
    '''
    try:
        tables = query_api.query(org=INFLUX_ORG, query=query)
        results = []
        for table in tables:
            for record in table.records:
                res = record.values.copy()
                res["timestamp"] = record.get_time().isoformat()
                res.pop("_time", None)
                res.pop("_measurement", None)
                res.pop("result", None)
                res.pop("table", None)
                res.pop("_start", None)
                res.pop("_stop", None)
                results.append(res)
        return results[:limit]
    except Exception as e:
        print(f"Influx query error: {e}")
        return []

# ─── Anomaly Results ─────────────────────────────────────────────

def insert_anomaly_result(timestamp: str, anomaly_score: float, is_anomaly: bool,
                          model_type: str = "isolation_forest",
                          fault_prediction: Optional[str] = None,
                          fault_probability: Optional[float] = None) -> int:
    """Insert an anomaly detection result."""
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO anomaly_results
        (timestamp, anomaly_score, is_anomaly, model_type, fault_prediction, fault_probability)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, anomaly_score, int(is_anomaly), model_type,
          fault_prediction, fault_probability))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def insert_anomaly_batch(results: list[dict]) -> int:
    """Insert multiple anomaly results."""
    conn = get_connection()
    for r in results:
        conn.execute("""
            INSERT INTO anomaly_results
            (timestamp, anomaly_score, is_anomaly, model_type, fault_prediction, fault_probability)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["timestamp"], r["anomaly_score"], int(r["is_anomaly"]),
              r.get("model_type", "isolation_forest"),
              r.get("fault_prediction"), r.get("fault_probability")))
    conn.commit()
    conn.close()
    return len(results)


def get_latest_anomaly(n: int = 1) -> list[dict]:
    """Get latest anomaly results."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM anomaly_results ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_anomaly_history(start: Optional[str] = None, end: Optional[str] = None,
                        limit: int = 500) -> list[dict]:
    """Get anomaly history with optional time range."""
    conn = get_connection()
    if start and end:
        rows = conn.execute(
            "SELECT * FROM anomaly_results WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp LIMIT ?",
            (start, end, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM anomaly_results ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_consecutive_anomalies(count: int = 5) -> int:
    """Count how many of the last N results are anomalies."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT is_anomaly FROM anomaly_results ORDER BY id DESC LIMIT ?", (count,)
    ).fetchall()
    conn.close()
    return sum(1 for r in rows if r["is_anomaly"])


# ─── Health Scores ───────────────────────────────────────────────

def insert_health_score(timestamp: str, health_score: float, risk_level: str,
                        anomaly_risk: float = 0, vibration_risk: float = 0,
                        temperature_risk: float = 0, force_risk: float = 0) -> int:
    """Insert a health score."""
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO health_scores
        (timestamp, health_score, risk_level, anomaly_risk, vibration_risk,
         temperature_risk, current_risk)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, health_score, risk_level, anomaly_risk,
          vibration_risk, temperature_risk, force_risk))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_latest_health(n: int = 1) -> list[dict]:
    """Get latest health score(s)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM health_scores ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_health_history(limit: int = 500) -> list[dict]:
    """Get health score history."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM health_scores ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


# ─── Fault Labels ────────────────────────────────────────────────

def insert_fault_label(start_timestamp: str, end_timestamp: str,
                       fault_type: str, severity: str = "medium",
                       notes: str = "", labeled_by: str = "operator") -> int:
    """Insert a fault label."""
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO fault_labels
        (start_timestamp, end_timestamp, fault_type, severity, notes, labeled_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (start_timestamp, end_timestamp, fault_type, severity, notes, labeled_by))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_fault_labels(limit: int = 100) -> list[dict]:
    """Get all fault labels."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM fault_labels ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_label_count() -> int:
    """Count total labeled events (for phase transition)."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM fault_labels").fetchone()[0]
    conn.close()
    return count



def get_labeled_training_data() -> list[dict]:
    """Get feature vectors with matching fault labels for supervised training (Influx + SQLite Join)."""
    conn = get_connection()
    labels = conn.execute("SELECT * FROM fault_labels ORDER BY start_timestamp").fetchall()
    conn.close()
    
    from database.influx_client import get_influx_client, INFLUX_BUCKET_FEATURES, INFLUX_ORG
    _, _, query_api = get_influx_client()
    if not query_api: return []
    
    labeled_features = []
    for lbl in labels:
        query = f'''
            from(bucket: "{INFLUX_BUCKET_FEATURES}")
            |> range(start: time(v: "{lbl["start_timestamp"]}"), stop: time(v: "{lbl["end_timestamp"]}"))
            |> filter(fn: (r) => r._measurement == "feature_vector")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        try:
            tables = query_api.query(org=INFLUX_ORG, query=query)
            for table in tables:
                for record in table.records:
                    res = record.values.copy()
                    res["timestamp"] = record.get_time().isoformat()
                    res["label"] = lbl["fault_type"]
                    res.pop("_time", None)
                    res.pop("_measurement", None)
                    res.pop("result", None)
                    res.pop("table", None)
                    res.pop("_start", None)
                    res.pop("_stop", None)
                    labeled_features.append(res)
        except Exception:
            pass
            
    return labeled_features

# ─── Alerts ──────────────────────────────────────────────────────

def insert_alert(timestamp: str, alert_type: str, severity: str,
                 message: str, health_score: Optional[float] = None) -> int:
    """Insert a new alert."""
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO alerts (timestamp, alert_type, severity, message, health_score)
        VALUES (?, ?, ?, ?, ?)
    """, (timestamp, alert_type, severity, message, health_score))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_alerts(acknowledged: Optional[bool] = None, limit: int = 100) -> list[dict]:
    """Get alerts with optional filter."""
    conn = get_connection()
    if acknowledged is not None:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE acknowledged = ? ORDER BY id DESC LIMIT ?",
            (int(acknowledged), limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def acknowledge_alert(alert_id: int) -> bool:
    """Acknowledge an alert."""
    conn = get_connection()
    conn.execute(
        "UPDATE alerts SET acknowledged = 1, acknowledged_at = ? WHERE id = ?",
        (datetime.now().isoformat(), alert_id)
    )
    conn.commit()
    conn.close()
    return True


def get_latest_alert_time() -> Optional[str]:
    """Get timestamp of the most recent alert."""
    conn = get_connection()
    row = conn.execute(
        "SELECT timestamp FROM alerts ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row["timestamp"] if row else None


def get_all_alerts() -> list[dict]:
    """Get all alerts from the database."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_fault_labels() -> list[dict]:
    """Get all human-labeled fault events."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM fault_labels ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

