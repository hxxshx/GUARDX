"""
GuardX — Isolation Forest Anomaly Detector (Layer 6 - Phase A)

Unsupervised anomaly detection using sklearn IsolationForest.
"""

import numpy as np
import os
import joblib
from sklearn.ensemble import IsolationForest
from config import (
    ISOLATION_FOREST_CONTAMINATION,
    ISOLATION_FOREST_N_ESTIMATORS,
    MODEL_DIR,
)


class IsolationForestDetector:
    """Isolation Forest for unsupervised anomaly detection."""

    def __init__(self):
        self.model = None
        self.model_path = os.path.join(MODEL_DIR, "isolation_forest.joblib")
        self.is_trained = False
        self._load_model()

    def train(self, features: np.ndarray) -> dict:
        """
        Train Isolation Forest on normal feature vectors using hyperparameter optimization.
        Performs a grid search to automatically select the best model.

        Args:
            features: numpy array of shape (n_samples, n_features)

        Returns:
            Training metrics dict including best params
        """
        import warnings
        from sklearn.metrics import silhouette_score
        
        # Grid parameters to search
        param_grid = {
            'contamination': [0.01, 0.05, 0.1],
            'max_samples': [0.8, 1.0, 256] # 256 is sklearn default
        }
        
        best_model = None
        best_score = -1
        best_params = {}
        
        # Total combinations = 3 x 3 = 9 variations (fast enough for real-time retraining)
        for cont in param_grid['contamination']:
            for samp in param_grid['max_samples']:
                
                # Max samples can't exceed dataset size
                if isinstance(samp, int) and samp > len(features):
                    samp = len(features)
                    
                model = IsolationForest(
                    n_estimators=ISOLATION_FOREST_N_ESTIMATORS,
                    contamination=cont,
                    max_samples=samp,
                    random_state=42,
                    n_jobs=-1,
                )
                
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model.fit(features)
                    
                # Evaluate using silhouette score (how well separated anomalies are)
                preds = model.predict(features)
                
                # Silhouette score requires at least 2 clusters and not all 1 cluster
                if len(set(preds)) > 1:
                    score = silhouette_score(features, preds)
                else:
                    score = -1 # Invalid if no anomalies found at all
                    
                if score > best_score:
                    best_score = score
                    best_model = model
                    best_params = {'contamination': cont, 'max_samples': samp}
        
        # Fallback if silhouette failed entirely
        if best_model is None:
            best_model = IsolationForest(
                n_estimators=ISOLATION_FOREST_N_ESTIMATORS,
                contamination=ISOLATION_FOREST_CONTAMINATION,
                random_state=42,
                n_jobs=-1,
            )
            best_model.fit(features)
            best_params = {'contamination': ISOLATION_FOREST_CONTAMINATION, 'max_samples': 'auto'}

        self.model = best_model
        self.is_trained = True
        self._save_model()

        # Compute training metrics on the winning model
        scores = self.model.decision_function(features)
        predictions = self.model.predict(features)
        anomaly_count = int(np.sum(predictions == -1))

        return {
            "n_samples": len(features),
            "n_anomalies_detected": anomaly_count,
            "anomaly_rate": anomaly_count / len(features),
            "mean_score": float(np.mean(scores)),
            "std_score": float(np.std(scores)),
            "best_params": best_params,
            "silhouette_score": round(float(best_score), 4) if best_score > -1 else 0
        }

    def predict(self, features: np.ndarray) -> list[dict]:
        """
        Predict anomalies for feature vectors.

        Args:
            features: numpy array of shape (n_samples, n_features)

        Returns:
            List of dicts with anomaly_score and is_anomaly
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        scores = self.model.decision_function(features)
        predictions = self.model.predict(features)

        results = []
        for i in range(len(features)):
            # Normalize score: more negative = more anomalous
            # Convert to 0-1 scale where 1 = most anomalous
            raw_score = float(scores[i])
            normalized_score = max(0, min(1, 0.5 - raw_score))

            results.append({
                "anomaly_score": round(normalized_score, 4),
                "is_anomaly": bool(predictions[i] == -1),
                "raw_score": round(raw_score, 4),
            })

        return results

    def predict_single(self, features: np.ndarray) -> dict:
        """Predict anomaly for a single feature vector."""
        return self.predict(features.reshape(1, -1))[0]

    def _save_model(self):
        """Persist model to disk."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(self.model, self.model_path)

    def _load_model(self):
        """Load model from disk if exists."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.is_trained = True
            except Exception:
                self.is_trained = False
