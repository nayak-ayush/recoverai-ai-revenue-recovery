"""
RecoverAI Feedback Loop & Training Dataset Export
Combines AI predictions with actual recovery outcomes for model improvement analysis.

IMPORTANT: This module does NOT automatically retrain the production model.
It exports data and checks feasibility. Retraining must be triggered manually.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MIN_RECORDS_FOR_RETRAINING = 50  # Minimum feedback records needed before retraining is suggested


def export_feedback_dataset(output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Export completed recovery outcomes combined with original AI prediction data
    into a structured feedback dataset suitable for future model retraining.

    Returns a dict with:
        - record_count
        - dataset (list of dicts)
        - retraining_feasible (bool)
        - message
        - exported_at
        - output_file (if written to disk)
    """
    from src.database import get_recovery_outcomes

    # Only use completed outcomes for training feedback
    completed_outcomes = get_recovery_outcomes(status=None, limit=None)
    completed = [o for o in completed_outcomes if o.get("status") in ("SUCCESS", "FAILED")]

    if not completed:
        return {
            "record_count": 0,
            "dataset": [],
            "retraining_feasible": False,
            "message": "No completed recovery outcomes available for feedback dataset.",
            "exported_at": datetime.now().isoformat(),
            "output_file": None
        }

    dataset = []
    for record in completed:
        is_recovered = record.get("outcome") == "RECOVERED"
        recovery_probability = record.get("recovery_probability")
        expected_recovery = record.get("expected_recovery") or 0.0
        recovered_amount = float(record.get("recovered_amount") or 0.0)
        payment_amount = float(record.get("payment_amount") or 0.0)

        # Calculate prediction feedback fields
        if recovery_probability is not None:
            prob = float(recovery_probability)
            prediction_correct = (prob >= 0.5 and is_recovered) or (prob < 0.5 and not is_recovered)
            prediction_error = (1.0 if is_recovered else 0.0) - prob
            actual_recovery_probability = 1.0 if is_recovered else 0.0
        else:
            prediction_correct = None
            prediction_error = None
            actual_recovery_probability = 1.0 if is_recovered else 0.0

        feedback_record = {
            # Original payment features (for model retraining)
            "payment_id": record.get("payment_id"),
            "customer_id": record.get("customer_id"),
            "payment_amount": payment_amount,
            "failure_reason": record.get("failure_reason"),
            "recommended_action": record.get("recommended_action"),
            "strategy": record.get("strategy"),
            "risk_level": record.get("risk_level"),
            "source": record.get("source", "SIMULATION"),

            # AI Prediction
            "predicted_recovery_probability": recovery_probability,
            "predicted_recovery_amount": expected_recovery,

            # Actual Outcome
            "actual_outcome": record.get("outcome"),
            "actual_status": record.get("status"),
            "actual_recovered_amount": recovered_amount,
            "actual_recovery_probability": actual_recovery_probability,
            "recovery_time_seconds": record.get("recovery_time_seconds"),

            # Feedback / Calibration Fields
            "prediction_correct": prediction_correct,
            "prediction_error": round(prediction_error, 4) if prediction_error is not None else None,
            "prediction_amount_error": round(abs(expected_recovery - recovered_amount), 2),

            # Metadata
            "outcome_id": record.get("id"),
            "decision_id": record.get("decision_id"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "feedback_exported_at": datetime.now().isoformat()
        }
        dataset.append(feedback_record)

    retraining_feasible = len(dataset) >= MIN_RECORDS_FOR_RETRAINING

    message = (
        f"Feedback dataset ready with {len(dataset)} records."
        if retraining_feasible
        else f"Insufficient feedback data for retraining. "
             f"Need {MIN_RECORDS_FOR_RETRAINING} completed records, have {len(dataset)}."
    )

    output_file = None
    if output_path and dataset:
        try:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(dataset, f, indent=2, default=str)
            output_file = str(out)
        except Exception as e:
            output_file = f"Error writing file: {str(e)}"

    return {
        "record_count": len(dataset),
        "dataset": dataset,
        "retraining_feasible": retraining_feasible,
        "message": message,
        "exported_at": datetime.now().isoformat(),
        "output_file": output_file,
        "min_required_for_retraining": MIN_RECORDS_FOR_RETRAINING
    }


def compute_per_outcome_feedback(outcome: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute prediction vs actual feedback fields for a single recovery outcome record.
    Used for per-record display in the dashboard.
    """
    recovery_probability = outcome.get("recovery_probability")
    outcome_status = str(outcome.get("outcome") or "").upper()
    is_recovered = outcome_status == "RECOVERED"
    expected_recovery = float(outcome.get("expected_recovery") or 0.0)
    recovered_amount = float(outcome.get("recovered_amount") or 0.0)

    if recovery_probability is not None:
        prob = float(recovery_probability)
        prediction_correct = (prob >= 0.5 and is_recovered) or (prob < 0.5 and not is_recovered)
        prediction_error = (1.0 if is_recovered else 0.0) - prob
        predicted_recovery_amount = expected_recovery
        actual_recovery_probability = 1.0 if is_recovered else 0.0
    else:
        prediction_correct = None
        prediction_error = None
        predicted_recovery_amount = None
        actual_recovery_probability = None

    return {
        "predicted_probability": recovery_probability,
        "actual_outcome": outcome_status,
        "actual_recovery_probability": actual_recovery_probability,
        "prediction_correct": prediction_correct,
        "prediction_error": round(prediction_error, 4) if prediction_error is not None else None,
        "predicted_recovery_amount": predicted_recovery_amount,
        "actual_recovered_amount": recovered_amount,
        "prediction_amount_error": round(abs(expected_recovery - recovered_amount), 2)
    }
