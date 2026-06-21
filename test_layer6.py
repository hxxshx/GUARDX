"""
Test Layer 6 — ML Intelligence Engine (Hardware-Aligned)
Verifies: Isolation Forest, Dynamic Thresholding, XGBoost + SHAP with 6 fault classes.
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

import numpy as np
from ml.engine import get_engine
from database import crud
from services.preprocessing import get_feature_vector_columns

def test_layer_6():
    print("--- Testing Layer 6 (Hardware-Aligned ML Engine) ---")
    
    engine = get_engine()
    
    # 1. Test GridSearchCV in Isolation Forest
    print("\n[1] Testing Isolation Forest with GridSearchCV...")
    cols = get_feature_vector_columns()
    n_features = len(cols)
    print(f"    Feature vector: {cols} ({n_features} features)")
    
    # 200 normal samples
    normal_data = np.random.normal(0, 1, (200, n_features))
    
    res_unsup = engine.train_unsupervised(normal_data)
    print("Unsupervised Training Result:", res_unsup)
    if "best_params" in res_unsup:
        print("GridSearchCV selected params:", res_unsup["best_params"])
        print("Silhouette Score:", res_unsup.get("silhouette_score"))
        
    # 2. Test Dynamic Thresholding
    print("\n[2] Testing Dynamic Alert Thresholding...")
    anomaly_data = np.random.normal(10, 5, (1, n_features))
    
    print("Sending 4 consecutive anomalies (Threshold is 5)...")
    for i in range(4):
        pred = engine.predict(anomaly_data)
        print(f" Reading {i+1} | raw_score: {pred[0]['anomaly_score']} | is_anomaly: {pred[0]['is_anomaly']} | Tracker: {engine.consecutive_anomalies}")
        
    print("Sending 5th anomaly (Should trigger is_anomaly=True)...")
    pred = engine.predict(anomaly_data)
    print(f" Reading 5 | raw_score: {pred[0]['anomaly_score']} | is_anomaly: {pred[0]['is_anomaly']} | Tracker: {engine.consecutive_anomalies}")
    
    if pred[0]['is_anomaly']:
        print("Dynamic thresholding works perfectly!")
        
    # 3. Test SHAP in XGBoost (ALL 6 FAULT CLASSES)
    print("\n[3] Testing SHAP Explainability in XGBoost...")
    labels = (
        ["normal"] * 100 + 
        ["bearing_wear"] * 40 + 
        ["imbalance"] * 20 +
        ["overheating"] * 20 +
        ["overload"] * 10 +
        ["coolant_failure"] * 10
    )
    X_train = np.vstack([
        np.random.normal(0, 1, (100, n_features)),     # normal
        np.random.normal(2, 0.5, (40, n_features)),     # bearing_wear
        np.random.normal(-2, 0.5, (20, n_features)),    # imbalance
        np.random.normal(0, 3, (20, n_features)),       # overheating
        np.random.normal(5, 5, (10, n_features)),       # overload
        np.random.normal(3, 2, (10, n_features)),       # coolant_failure
    ])
    
    # Mock crud for testing
    original_get_labeled = crud.get_labeled_training_data
    original_get_count = crud.get_label_count
    
    mock_labeled = []
    for i in range(200):
        d = {"label": labels[i]}
        for j, c in enumerate(cols):
            d[c] = X_train[i, j]
        mock_labeled.append(d)
        
    crud.get_labeled_training_data = lambda: mock_labeled
    crud.get_label_count = lambda: 200  # Force Phase C
    
    res_sup = engine.train_supervised()
    print("Supervised Training Result:", res_sup)
    
    # Predict a bearing wear anomaly to see SHAP output
    test_anomaly = np.random.normal(2, 0.5, (1, n_features))
    pred_sup = engine.predict(test_anomaly)
    
    print("Prediction with SHAP Explainability:")
    print("Predicted Fault:", pred_sup[0]["fault_prediction"])
    print("Confidence:", pred_sup[0]["fault_probability"])
    print("SHAP Text Explanation:", pred_sup[0].get("explanation"))
    print("SHAP Data:", pred_sup[0].get("explanation_data"))
    
    # Restore crud
    crud.get_labeled_training_data = original_get_labeled
    crud.get_label_count = original_get_count

if __name__ == "__main__":
    test_layer_6()
