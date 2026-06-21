"""
GuardX — Model Retraining Pipeline (Layer 6)

Periodic retraining scheduler that fetches latest data
and retrains models.
"""

from datetime import datetime
from ml.engine import get_engine
from database import crud


def run_retraining() -> dict:
    """
    Execute full retraining pipeline.
    Called by scheduler or manually via API.
    """
    engine = get_engine()
    result = engine.retrain()
    return {
        "timestamp": datetime.now().isoformat(),
        "result": result,
    }


def check_phase_transition() -> dict:
    """
    Check if ML phase should transition based on label count.
    """
    engine = get_engine()
    label_count = crud.get_label_count()
    current = engine.current_phase

    return {
        "current_phase": current,
        "label_count": label_count,
        "phase_description": engine.phase_description,
    }
