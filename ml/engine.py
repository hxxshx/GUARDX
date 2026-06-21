from typing import Optional
"""
GuardX — ML Engine Orchestrator (Layer 6)

Manages the 3-phase learning lifecycle:
  Phase A: Unsupervised (Isolation Forest only)
  Phase B: Hybrid (Isolation Forest + XGBoost)
  Phase C: Fully Supervised (XGBoost primary, IF as safety net)
"""

import numpy as np
from datetime import datetime
from ml.isolation_forest import IsolationForestDetector
from ml.classifier import FaultClassifier
from database import crud
from services.preprocessing import features_to_array, get_feature_vector_columns
from config import ML_PHASE_B_THRESHOLD, ML_PHASE_C_THRESHOLD, ANOMALY_PERSISTENCE_COUNT


class MLEngine:
    """Core ML orchestrator that manages phase transitions and predictions."""

    def __init__(self):
        self.if_detector = IsolationForestDetector()
        self.classifier = FaultClassifier()
        self.last_training_time = None
        self.consecutive_anomalies = 0

    @property
    def current_phase(self) -> str:
        """Determine current ML phase based on labeled data count."""
        label_count = crud.get_label_count()
        if label_count >= ML_PHASE_C_THRESHOLD and self.classifier.is_trained:
            return "C"
        elif label_count >= ML_PHASE_B_THRESHOLD and self.classifier.is_trained:
            return "B"
        return "A"

    @property
    def phase_description(self) -> str:
        """Human-readable phase description."""
        descriptions = {
            "A": "Unsupervised Mode - Isolation Forest anomaly detection",
            "B": "Hybrid Mode - Anomaly detection + Fault classification",
            "C": "Supervised Mode - Full fault prediction with anomaly safety net",
        }
        return descriptions[self.current_phase]

    def get_status(self) -> dict:
        """Get complete ML engine status."""
        return {
            "current_phase": self.current_phase,
            "phase_description": self.phase_description,
            "labeled_count": crud.get_label_count(),
            "phase_b_threshold": ML_PHASE_B_THRESHOLD,
            "phase_c_threshold": ML_PHASE_C_THRESHOLD,
            "unsupervised_model_loaded": self.if_detector.is_trained,
            "supervised_model_loaded": self.classifier.is_trained,
            "last_training_time": self.last_training_time,
            "classifier_metrics": self.classifier.metrics if self.classifier.is_trained else None,
        }

    def train_unsupervised(self, features: Optional[np.ndarray] = None) -> dict:
        """
        Train the Isolation Forest on feature vectors.
        If no features provided, fetches from database.
        """
        if features is None:
            feature_dicts = crud.get_features_for_training()
            if not feature_dicts:
                return {"status": "error", "message": "No feature data available"}
            features = features_to_array(feature_dicts)

        metrics = self.if_detector.train(features)
        self.last_training_time = datetime.now().isoformat()
        return {"status": "ok", "model": "isolation_forest", **metrics}

    def train_supervised(self) -> dict:
        """
        Train the fault classifier on labeled data.
        Only works when sufficient labeled data exists.
        """
        labeled_data = crud.get_labeled_training_data()
        if len(labeled_data) < ML_PHASE_B_THRESHOLD:
            return {
                "status": "insufficient_data",
                "message": f"Need {ML_PHASE_B_THRESHOLD} labels, have {len(labeled_data)}",
            }

        cols = get_feature_vector_columns()
        features = np.array([[d.get(c, 0) for c in cols] for d in labeled_data])
        labels = [d["label"] for d in labeled_data]

        metrics = self.classifier.train(features, labels)
        self.last_training_time = datetime.now().isoformat()
        return {"status": "ok", "model": "xgboost_classifier", **metrics}

    def predict(self, features: np.ndarray) -> list[dict]:
        """
        Run prediction based on current phase.

        Args:
            features: numpy array of shape (n_samples, n_features)

        Returns:
            List of prediction dicts with anomaly and classification info
        """
        results = []
        phase = self.current_phase

        # Phase A: Unsupervised only fallback (lazy loading if predicting before train)
        if phase == "A" and not self.if_detector.is_trained:
            # Auto-train on first run if data available
            feature_dicts = crud.get_features_for_training(limit=5000)
            if feature_dicts:
                train_features = features_to_array(feature_dicts)
                self.if_detector.train(train_features)
            else:
                return [{"anomaly_score": 0.0, "is_anomaly": False,
                         "model_type": "none", "fault_prediction": None,
                         "fault_probability": None}] * len(features)

        # Determine results for each feature vector
        class_results = None
        if phase != "A" and self.classifier.is_trained:
            class_results = self.classifier.predict(features)
            
        anomaly_results = self.if_detector.predict(features)

        for i in range(len(features)):
            ar = anomaly_results[i]
            cr = class_results[i] if class_results else None

            # Raw prediction logic
            if phase == "C" and cr:
                # Supervised primary, unsupervised as safety net
                raw_anomaly = ar["is_anomaly"] or cr["fault_prediction"] != "normal"
            else:
                # Phase A/B: Unsupervised driven anomaly flag
                raw_anomaly = ar["is_anomaly"]

            # Dynamic Thresholding: Track consecutive anomalies to reduce false alarms
            if raw_anomaly:
                self.consecutive_anomalies += 1
            else:
                self.consecutive_anomalies = 0

            # Only flag actual actionable anomaly if persistence threshold is met
            is_anomaly = self.consecutive_anomalies >= ANOMALY_PERSISTENCE_COUNT

            results.append({
                "anomaly_score": ar["anomaly_score"],
                "is_anomaly": is_anomaly,
                "model_type": f"hybrid_phase_{phase.lower()}" if phase != "A" else "isolation_forest",
                "fault_prediction": cr["fault_prediction"] if cr else None,
                "fault_probability": cr["fault_probability"] if cr else None,
                "explanation": cr.get("explanation") if cr else None,
                "explanation_data": cr.get("explanation_data") if cr else None,
            })

        return results

    def retrain(self) -> dict:
        """Full retraining pipeline."""
        result = {"unsupervised": None, "supervised": None}

        # Always retrain unsupervised
        result["unsupervised"] = self.train_unsupervised()

        # Train supervised if enough labels
        label_count = crud.get_label_count()
        if label_count >= ML_PHASE_B_THRESHOLD:
            result["supervised"] = self.train_supervised()

        self.last_training_time = datetime.now().isoformat()
        return result


# Singleton instance
_engine: Optional[MLEngine] = None

def get_engine() -> MLEngine:
    """Get or create the singleton ML engine."""
    global _engine
    if _engine is None:
        _engine = MLEngine()
    return _engine
