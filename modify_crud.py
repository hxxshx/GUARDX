import os

FILE_PATH = "c:/Users/Keerthi Sridhar/Desktop/GAURDX/database/crud.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith("# ─── Raw Sensor Data ─────────────────────────────────────────────"):
        skip = True
        new_lines.append(line)
        new_lines.append('''
def insert_raw_reading(vibration: float, temperature: float, current: float,
                       timestamp: str | None = None,
                       machine_id: str = "CNC-01",
                       sensor_id: str = "MAIN-01") -> int:
    from database.influx_client import write_raw_reading
    from datetime import datetime
    ts = timestamp or datetime.now().isoformat()
    success = write_raw_reading(vibration, temperature, current, ts, machine_id, sensor_id)
    return 1 if success else 0


def insert_raw_batch(readings: list[dict]) -> int:
    from database.influx_client import write_raw_batch
    success = write_raw_batch(readings)
    return len(readings) if success else 0


def get_latest_raw(n: int = 60) -> list[dict]:
    from database.influx_client import get_influx_client, INFLUX_BUCKET_RAW, INFLUX_ORG
    _, _, query_api = get_influx_client()
    if not query_api: return []
    query = f\'\'\'
        from(bucket: "{INFLUX_BUCKET_RAW}")
        |> range(start: -1d)
        |> filter(fn: (r) => r._measurement == "sensor_reading")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: true)
        |> limit(n: {n})
    \'\'\'
    try:
        tables = query_api.query(org=INFLUX_ORG, query=query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "timestamp": record.get_time().isoformat(),
                    "machine_id": record.values.get("machine_id"),
                    "sensor_id": record.values.get("sensor_id"),
                    "vibration": record.values.get("vibration"),
                    "temperature": record.values.get("temperature"),
                    "current": record.values.get("current")
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
    query = f\'\'\'
        from(bucket: "{INFLUX_BUCKET_RAW}")
        |> range(start: time(v: "{start}"), stop: time(v: "{end}"))
        |> filter(fn: (r) => r._measurement == "sensor_reading")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: false)
    \'\'\'
    try:
        tables = query_api.query(org=INFLUX_ORG, query=query)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "timestamp": record.get_time().isoformat(),
                    "machine_id": record.values.get("machine_id"),
                    "sensor_id": record.values.get("sensor_id"),
                    "vibration": record.values.get("vibration"),
                    "temperature": record.values.get("temperature"),
                    "current": record.values.get("current")
                })
        results.sort(key=lambda x: x["timestamp"])
        return results
    except Exception as e:
        print(e)
        return []


def get_raw_count() -> int:
    return 1000 # Dummy for influx


def get_unprocessed_raw(last_processed_time: str | None = None, limit: int = 100) -> list[dict]:
    from database.influx_client import get_influx_client, INFLUX_BUCKET_RAW, INFLUX_ORG
    _, _, query_api = get_influx_client()
    if not query_api: return []
    start_time = f\'time(v: "{last_processed_time}")\' if last_processed_time else "-1h"
    query = f\'\'\'
        from(bucket: "{INFLUX_BUCKET_RAW}")
        |> range(start: {start_time})
        |> filter(fn: (r) => r._measurement == "sensor_reading")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: false)
        |> limit(n: {limit})
    \'\'\'
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
                        "vibration": record.values.get("vibration"),
                        "temperature": record.values.get("temperature"),
                        "current": record.values.get("current")
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
    query = f\'\'\'
        from(bucket: "{INFLUX_BUCKET_FEATURES}")
        |> range(start: -1d)
        |> filter(fn: (r) => r._measurement == "feature_vector")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: true)
        |> limit(n: {n})
    \'\'\'
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
    query = f\'\'\'
        from(bucket: "{INFLUX_BUCKET_FEATURES}")
        |> range(start: -30d)
        |> filter(fn: (r) => r._measurement == "feature_vector")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: false)
        |> limit(n: {limit})
    \'\'\'
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

''')
    elif line.startswith("# ─── Anomaly Results ─────────────────────────────────────────────"):
        skip = False
    
    if line.startswith("def get_labeled_training_data() -> list[dict]:"):
        skip = True
        new_lines.append('''
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
        query = f\'\'\'
            from(bucket: "{INFLUX_BUCKET_FEATURES}")
            |> range(start: time(v: "{lbl["start_timestamp"]}"), stop: time(v: "{lbl["end_timestamp"]}"))
            |> filter(fn: (r) => r._measurement == "feature_vector")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        \'\'\'
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

''')
    elif skip and line.startswith("# ─── Alerts ──────────────────────────────────────────────────────"):
        skip = False

    if not skip:
        new_lines.append(line)

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("CRUD file modified successfully.")
