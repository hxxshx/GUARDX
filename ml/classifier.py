"""
GuardX — Supervised Fault Classifier (Layer 6 - Phase B/C)

XGBoost-based fault classification for labeled data.
"""

import numpy as np
import os
import joblib

try:
    from xgboost import XGBClassifier
except ImportError:
    from sklearn.ensemble import RandomForestClassifier as XGBClassifier

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from config import MODEL_DIR


FAULT_CLASSES = ["normal", "bearing_wear", "imbalance", "overheating", "overload", "coolant_failure"]


class FaultClassifier:
    """XGBoost/RandomForest fault type classifier."""

    def __init__(self):
        self.model = None
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(FAULT_CLASSES)
        self.model_path = os.path.join(MODEL_DIR, "classifier.joblib")
        self.encoder_path = os.path.join(MODEL_DIR, "label_encoder.joblib")
        self.is_trained = False
        self.metrics = {}
        self._load_model()

    def train(self, features: np.ndarray, labels: list[str]) -> dict:
        """
        Train fault classifier.

        Args:
            features: numpy array of shape (n_samples, n_features)
            labels: list of fault type strings

        Returns:
            Training metrics dict
        """
        encoded_labels = self.label_encoder.transform(labels)

        # Split for evaluation
        X_train, X_test, y_train, y_test = train_test_split(
            features, encoded_labels, test_size=0.2, random_state=42,
            stratify=encoded_labels if len(set(encoded_labels)) > 1 else None
        )

        try:
            self.model = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                use_label_encoder=False,
                eval_metric="mlogloss",
            )
        except TypeError:
            # Fallback for RandomForest (if XGBoost not available)
            self.model = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                random_state=42,
            )

        self.model.fit(X_train, y_train)
        self.is_trained = True

        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = float(accuracy_score(y_test, y_pred))

        self.metrics = {
            "accuracy": accuracy,
            "n_train": len(X_train),
            "n_test": len(X_test),
            "classes": list(self.label_encoder.classes_),
        }

        self._save_model()
        return self.metrics

    def predict(self, features: np.ndarray) -> list[dict]:
        """
        Predict fault type for feature vectors and generate SHAP explanations.

        Args:
            features: numpy array of shape (n_samples, n_features)

        Returns:
            List of dicts with fault_type, probabilities, and SHAP explanations
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        # Ensure features is 2D
        if len(features.shape) == 1:
            features = features.reshape(1, -1)

        predictions = self.model.predict(features)
        try:
            probabilities = self.model.predict_proba(features)
        except AttributeError:
            probabilities = np.zeros((len(features), len(FAULT_CLASSES)))

        # --- SHAP Explainability Logic ---
        shap_explanations = []
        try:
            import shap
            from services.preprocessing import get_feature_vector_columns
            
            # Using TreeExplainer which is highly optimized for XGBoost/RandomForest
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(features)
            
            feature_names = get_feature_vector_columns()
            
            # Extract top contributing features per prediction
            for i in range(len(features)):
                pred_class_idx = predictions[i]
                
                # Handling different formats returned by shap_values depending on sklearn/xgboost version
                if isinstance(shap_values, list):
                    # Multi-class format
                    instance_shap = shap_values[pred_class_idx][i]
                elif len(shap_values.shape) == 3:
                     # Some newer versions return 3D arrays for multi-class
                    instance_shap = shap_values[i, :, pred_class_idx]
                else:
                    # Binary or older version
                    instance_shap = shap_values[i]
                
                # Pair features with their shap values & absolute shap values (for sorting importance)
                feature_importance = [
                    {"feature": name, "shap_value": float(val), "abs_val": abs(float(val))}
                    for name, val in zip(feature_names, instance_shap)
                ]
                
                # Sort by absolute contribution (most important driving factors first)
                feature_importance.sort(key=lambda x: x["abs_val"], reverse=True)
                
                # Format the top 3 text explanation
                top_3 = feature_importance[:3]
                expl_text = [f"{f['feature']}: {'+' if f['shap_value'] > 0 else ''}{f['shap_value']:.2f}" for f in top_3]
                
                shap_explanations.append({
                    "top_features": [{"feature": f["feature"], "impact": f["shap_value"]} for f in top_3],
                    "text_explanation": "Drivers: " + ", ".join(expl_text)
                })
        except Exception as e:
            print(f"SHAP explanation failed: {e}")
            # Fallback if SHAP fails or features mismatch
            shap_explanations = [{"top_features": [], "text_explanation": "Explanation unavailable"} for _ in range(len(features))]

        # --- Combine Results ---
        results = []
        for i in range(len(features)):
            fault_type = self.label_encoder.inverse_transform([predictions[i]])[0]
            proba = probabilities[i] if i < len(probabilities) else []

            results.append({
                "fault_prediction": fault_type,
                "fault_probability": float(max(proba)) if len(proba) > 0 else 0.0,
                "probabilities": {
                    cls: round(float(p), 4)
                    for cls, p in zip(self.label_encoder.classes_, proba)
                } if len(proba) > 0 else {},
                "explanation": shap_explanations[i]["text_explanation"],
                "explanation_data": shap_explanations[i]["top_features"]
            })

        return results

    def predict_single(self, features: np.ndarray) -> dict:
        """Predict fault type for a single feature vector."""
        return self.predict(features.reshape(1, -1))[0]

    def _save_model(self):
        """Persist model and encoder to disk."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.label_encoder, self.encoder_path)

    def _load_model(self):
        """Load model from disk if exists."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                if os.path.exists(self.encoder_path):
                    self.label_encoder = joblib.load(self.encoder_path)
                self.is_trained = True
            except Exception:
                self.is_trained = False
