"""
GuardX — Background Scheduler

Runs periodic tasks: preprocessing, ML inference, health scoring, alert checks.
"""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from config import PROCESSING_INTERVAL, INFERENCE_INTERVAL, HEALTH_INTERVAL

# Track processing state using timestamp for InfluxDB compatibility
_last_processed_time = None


def process_raw_data():
    """Process unprocessed raw readings into features."""
    global _last_processed_time
    from database import crud
    from services.preprocessing import preprocess_readings

    readings = crud.get_unprocessed_raw(_last_processed_time, limit=50)
    if not readings:
        return

    features = preprocess_readings(readings)
    if features:
        crud.insert_processed_features(features)
        _last_processed_time = readings[-1]["timestamp"]


def run_inference():
    """Run ML inference on latest features."""
    from database import crud
    from services.preprocessing import features_to_array
    from ml.engine import get_engine

    features = crud.get_latest_features(n=10)
    if not features:
        return

    engine = get_engine()
    if not engine.if_detector.is_trained:
        # Need to train first
        all_features = crud.get_features_for_training(limit=5000)
        if len(all_features) >= 100:
            arr = features_to_array(all_features)
            engine.train_unsupervised(arr)
        else:
            return

    arr = features_to_array(features)
    results = engine.predict(arr)

    # Store results with timestamps
    for feat, res in zip(features, results):
        res["timestamp"] = feat["timestamp"]

    crud.insert_anomaly_batch(results)


def compute_health():
    """Compute health scores for latest data."""
    from database import crud
    from services.health_engine import compute_health_score

    anomalies = crud.get_latest_anomaly(n=1)
    features = crud.get_latest_features(n=1)

    if not anomalies or not features:
        return

    a = anomalies[-1]
    f = features[-1]

    compute_health_score(
        anomaly_score=a.get("anomaly_score", 0),
        vibration_rms=f.get("vibration_rms", 0.08),
        temperature=f.get("temperature", 32.0),
        cutting_force=f.get("cutting_force", 8.0),
        timestamp=f.get("timestamp"),
    )


def start_scheduler() -> BackgroundScheduler:
    """Start the background scheduler with all jobs."""
    scheduler = BackgroundScheduler()

    scheduler.add_job(process_raw_data, "interval", seconds=PROCESSING_INTERVAL,
                      id="process_raw", replace_existing=True)
    scheduler.add_job(run_inference, "interval", seconds=INFERENCE_INTERVAL,
                      id="run_inference", replace_existing=True)
    scheduler.add_job(compute_health, "interval", seconds=HEALTH_INTERVAL,
                      id="compute_health", replace_existing=True)

    scheduler.start()
    return scheduler
