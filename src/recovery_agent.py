import sys
import pandas as pd
import joblib
from pathlib import Path
from typing import Dict, Any

# ==========================================
# Paths configuration
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODEL_FILE = PROJECT_ROOT / "models" / "recovery_model.pkl"

from src.ranking_engine import calculate_opportunity_score

model = joblib.load(MODEL_FILE)


# ==========================================
# Recovery Agent
# ==========================================

def recovery_agent(payment: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI-Powered Recovery Agent with Intelligent Opportunity Ranking.
    1. Runs ML model to predict recovery probability.
    2. Enforces safety rules to prevent risky automatic retries.
    3. Calculates intelligent Revenue Opportunity Score & priority level.
    """
    # Extract identifiers or generate fallbacks
    payment_id = payment.get("payment_id")
    customer_id = payment.get("customer_id")
    payment_method = payment.get("payment_method", "card")
    retry_count = int(payment.get("retry_count", 0))

    # Convert payment into DataFrame for ML model prediction
    # Features required by model:
    # amount, payment_method, failure_reason, previous_payments, previous_failures,
    # days_since_last_payment, subscription, hour, is_weekend
    features_dict = {
        "amount": payment.get("amount", 0.0),
        "payment_method": payment_method,
        "failure_reason": payment.get("failure_reason", "network_timeout"),
        "previous_payments": payment.get("previous_payments", 0),
        "previous_failures": payment.get("previous_failures", 0),
        "days_since_last_payment": payment.get("days_since_last_payment", 0),
        "subscription": payment.get("subscription", 0),
        "hour": payment.get("hour", 12),
        "is_weekend": payment.get("is_weekend", 0)
    }
    data = pd.DataFrame([features_dict])

    # Get probability from ML model
    probability = float(model.predict_proba(data)[0][1])

    # Expected recoverable revenue
    amount = float(payment.get("amount", 0.0))
    expected_revenue = amount * probability

    # ======================================
    # Safety rules
    # ======================================
    failure_reason = payment.get("failure_reason", "network_timeout")

    # Permanent / risky failures
    permanent_failures = [
        "bank_decline",
        "authentication_failed",
        "expired_card"
    ]

    if failure_reason in permanent_failures:
        action = "CUSTOMER_ACTION_REQUIRED"
        risk = "HIGH"
        reason = (
            "Automatic retry is not recommended "
            "for this failure type."
        )
    elif probability >= 0.80:
        action = "RETRY_PAYMENT"
        risk = "LOW"
        reason = (
            "High recovery probability and "
            "recoverable payment failure."
        )
    elif probability >= 0.60:
        action = "SCHEDULE_RETRY"
        risk = "MEDIUM"
        reason = (
            "Moderate recovery probability. "
            "Retry should be delayed."
        )
    elif probability >= 0.40:
        action = "SEND_PAYMENT_REMINDER"
        risk = "MEDIUM"
        reason = (
            "Recovery is possible but automatic "
            "retry is not optimal."
        )
    else:
        action = "STOP_AUTOMATIC_RECOVERY"
        risk = "HIGH"
        reason = (
            "Low recovery probability. "
            "Avoid unnecessary recovery attempts."
        )

    # ======================================
    # Calculate Intelligent Revenue Opportunity Score
    # ======================================
    opportunity_result = calculate_opportunity_score(
        payment_amount=amount,
        recovery_probability=probability,
        expected_revenue=expected_revenue,
        recommended_action=action,
        failure_reason=failure_reason,
        customer_info={
            "previous_payments": payment.get("previous_payments", 0),
            "previous_failures": payment.get("previous_failures", 0),
            "subscription": payment.get("subscription", 0)
        },
        retry_count=retry_count
    )

    # ======================================
    # Agent decision
    # ======================================
    decision = {
        "payment_id": payment_id,
        "customer_id": customer_id,
        "payment_amount": amount,
        "payment_method": payment_method,
        "failure_reason": failure_reason,
        "recovery_probability": round(probability, 4),
        "recovery_percentage": round(probability * 100, 2),
        "expected_revenue": round(expected_revenue, 2),
        "risk_level": risk,
        "recommended_action": action,
        "retry_count": retry_count,
        "revenue_opportunity_score": opportunity_result["revenue_opportunity_score"],
        "priority_level": opportunity_result["priority_level"],
        "reason": reason,
        "explanation": opportunity_result["explanation"],
        "sub_scores": opportunity_result["sub_scores"]
    }

    return decision


# ==========================================
# Test the agent
# ==========================================

if __name__ == "__main__":
    payment_sample = {
        "payment_id": "PAY00125",
        "customer_id": "CUST0182",
        "amount": 15000,
        "payment_method": "card",
        "failure_reason": "network_timeout",
        "previous_payments": 15,
        "previous_failures": 1,
        "days_since_last_payment": 5,
        "subscription": 1,
        "hour": 14,
        "is_weekend": 0
    }

    result = recovery_agent(payment_sample)

    print("=" * 60)
    print("              RECOVERAI AGENT")
    print("=" * 60)

    for key, value in result.items():
        try:
            print(f"{key}: {value}")
        except UnicodeEncodeError:
            print(f"{key}: {str(value).encode('ascii', 'replace').decode('ascii')}")

    print("=" * 60)