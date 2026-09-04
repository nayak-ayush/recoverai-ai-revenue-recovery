"""
RecoverAI Recovery Outcome Seed Data Utility
Creates clearly labeled SIMULATION/DEMO recovery outcome records for dashboard demonstration.

IMPORTANT:
- This script NEVER modifies real customer or payment data.
- All records are labeled source='SIMULATION'.
- Running it multiple times safely checks for existing demo data.
- Do NOT run this automatically at API startup.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import (
    create_database,
    get_connection,
    record_recovery_attempt,
    advance_outcome_to_attempted,
    save_recovery_outcome
)

# Demo scenarios: diverse strategies, failure reasons, outcomes
DEMO_SCENARIOS = [
    {"payment_id": "DEMO-PAY-001", "customer_id": "DEMO-CUST-01", "amount": 15000, "action": "RETRY_PAYMENT", "failure_reason": "network_timeout", "prob": 0.87, "outcome": "RECOVERED", "recovered": 15000, "time": 120},
    {"payment_id": "DEMO-PAY-002", "customer_id": "DEMO-CUST-02", "amount": 5000,  "action": "RETRY_PAYMENT", "failure_reason": "technical_error", "prob": 0.82, "outcome": "RECOVERED", "recovered": 5000, "time": 95},
    {"payment_id": "DEMO-PAY-003", "customer_id": "DEMO-CUST-03", "amount": 25000, "action": "SCHEDULE_RETRY", "failure_reason": "insufficient_balance", "prob": 0.62, "outcome": "RECOVERED", "recovered": 25000, "time": 3600},
    {"payment_id": "DEMO-PAY-004", "customer_id": "DEMO-CUST-04", "amount": 8000,  "action": "CUSTOMER_ACTION_REQUIRED", "failure_reason": "authentication_failed", "prob": 0.45, "outcome": "NOT_RECOVERED", "recovered": 0, "time": None, "reason": "Customer did not complete authentication"},
    {"payment_id": "DEMO-PAY-005", "customer_id": "DEMO-CUST-05", "amount": 12000, "action": "RETRY_PAYMENT", "failure_reason": "network_timeout", "prob": 0.91, "outcome": "RECOVERED", "recovered": 12000, "time": 185},
    {"payment_id": "DEMO-PAY-006", "customer_id": "DEMO-CUST-06", "amount": 3500,  "action": "SEND_PAYMENT_REMINDER", "failure_reason": "bank_decline", "prob": 0.30, "outcome": "NOT_RECOVERED", "recovered": 0, "time": None, "reason": "Bank declined repeatedly"},
    {"payment_id": "DEMO-PAY-007", "customer_id": "DEMO-CUST-07", "amount": 18000, "action": "RETRY_PAYMENT", "failure_reason": "technical_error", "prob": 0.85, "outcome": "RECOVERED", "recovered": 18000, "time": 145},
    {"payment_id": "DEMO-PAY-008", "customer_id": "DEMO-CUST-08", "amount": 9500,  "action": "SCHEDULE_RETRY", "failure_reason": "insufficient_balance", "prob": 0.55, "outcome": "RETRY_FAILED", "recovered": 0, "time": None, "reason": "Insufficient funds at retry time"},
    {"payment_id": "DEMO-PAY-009", "customer_id": "DEMO-CUST-09", "amount": 22000, "action": "RETRY_PAYMENT", "failure_reason": "network_timeout", "prob": 0.78, "outcome": "RECOVERED", "recovered": 22000, "time": 220},
    {"payment_id": "DEMO-PAY-010", "customer_id": "DEMO-CUST-10", "amount": 6000,  "action": "CUSTOMER_ACTION_REQUIRED", "failure_reason": "expired_card", "prob": 0.40, "outcome": "CUSTOMER_ACTION_REQUIRED", "recovered": 0, "time": None, "reason": "Customer needs to update card details"},
    {"payment_id": "DEMO-PAY-011", "customer_id": "DEMO-CUST-11", "amount": 14500, "action": "RETRY_PAYMENT", "failure_reason": "technical_error", "prob": 0.83, "outcome": "RECOVERED", "recovered": 14500, "time": 105},
    {"payment_id": "DEMO-PAY-012", "customer_id": "DEMO-CUST-12", "amount": 7800,  "action": "SCHEDULE_RETRY", "failure_reason": "network_timeout", "prob": 0.67, "outcome": "RECOVERED", "recovered": 7800, "time": 1800},
    {"payment_id": "DEMO-PAY-013", "customer_id": "DEMO-CUST-13", "amount": 30000, "action": "RETRY_PAYMENT", "failure_reason": "technical_error", "prob": 0.89, "outcome": "RECOVERED", "recovered": 30000, "time": 162},
    {"payment_id": "DEMO-PAY-014", "customer_id": "DEMO-CUST-14", "amount": 4200,  "action": "STOP_AUTOMATIC_RECOVERY", "failure_reason": "bank_decline", "prob": 0.22, "outcome": "NOT_RECOVERED", "recovered": 0, "time": None, "reason": "Recovery probability too low"},
    {"payment_id": "DEMO-PAY-015", "customer_id": "DEMO-CUST-15", "amount": 19000, "action": "RETRY_PAYMENT", "failure_reason": "network_timeout", "prob": 0.92, "outcome": "RECOVERED", "recovered": 19000, "time": 175},
    {"payment_id": "DEMO-PAY-016", "customer_id": "DEMO-CUST-16", "amount": 11000, "action": "SEND_PAYMENT_REMINDER", "failure_reason": "insufficient_balance", "prob": 0.44, "outcome": "RECOVERED", "recovered": 11000, "time": 7200},
    {"payment_id": "DEMO-PAY-017", "customer_id": "DEMO-CUST-17", "amount": 2500,  "action": "SCHEDULE_RETRY", "failure_reason": "technical_error", "prob": 0.61, "outcome": "RETRY_FAILED", "recovered": 0, "time": None, "reason": "Max retries exceeded"},
    {"payment_id": "DEMO-PAY-018", "customer_id": "DEMO-CUST-18", "amount": 16500, "action": "RETRY_PAYMENT", "failure_reason": "network_timeout", "prob": 0.86, "outcome": "RECOVERED", "recovered": 16500, "time": 135},
    {"payment_id": "DEMO-PAY-019", "customer_id": "DEMO-CUST-19", "amount": 5500,  "action": "CUSTOMER_ACTION_REQUIRED", "failure_reason": "authentication_failed", "prob": 0.38, "outcome": "EXPIRED", "recovered": 0, "time": None, "reason": "Recovery window expired"},
    {"payment_id": "DEMO-PAY-020", "customer_id": "DEMO-CUST-20", "amount": 28000, "action": "RETRY_PAYMENT", "failure_reason": "technical_error", "prob": 0.93, "outcome": "RECOVERED", "recovered": 28000, "time": 195},
]

# Map from custom outcome string to what save_recovery_outcome expects
OUTCOME_MAP = {
    "RECOVERED": "RECOVERED",
    "NOT_RECOVERED": "NOT_RECOVERED",
    "CUSTOMER_ACTION_REQUIRED": "CUSTOMER_ACTION_REQUIRED",
    "RETRY_FAILED": "RETRY_FAILED",
    "EXPIRED": "EXPIRED"
}


def check_existing_demo_data() -> int:
    """Return count of existing SIMULATION outcome records."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM recovery_outcomes WHERE source = 'SIMULATION'")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def seed_recovery_outcomes(force: bool = False) -> Dict[str, Any]:
    """
    Seed demo recovery outcomes into the database.

    Args:
        force: If True, add records even if demo data already exists.

    Returns:
        Summary of seeding operation.
    """
    from typing import Dict, Any

    create_database()

    existing_count = check_existing_demo_data()

    if existing_count >= len(DEMO_SCENARIOS) and not force:
        return {
            "seeded": False,
            "existing_records": existing_count,
            "message": f"Demo data already present ({existing_count} SIMULATION records). Use force=True to add more.",
            "skipped": True
        }

    seeded = 0
    errors = []

    for i, scenario in enumerate(DEMO_SCENARIOS):
        try:
            # Create the attempt in PENDING state
            outcome_id = record_recovery_attempt(
                payment_id=scenario["payment_id"],
                customer_id=scenario["customer_id"],
                recommended_action=scenario["action"],
                executed_action=scenario["action"],
                recovery_probability=scenario["prob"],
                risk_level="HIGH" if scenario["prob"] < 0.4 else ("MEDIUM" if scenario["prob"] < 0.7 else "LOW"),
                payment_amount=scenario["amount"],
                expected_recovery=scenario["amount"] * scenario["prob"],
                opportunity_score=scenario["prob"] * 100,
                revenue_at_risk=scenario["amount"],
                failure_reason=scenario["failure_reason"],
                strategy=scenario["action"],
                reason=scenario.get("reason", "Demo simulation record"),
                source="SIMULATION",
                actor="SEED_SCRIPT"
            )

            # Advance to ATTEMPTED
            advance_outcome_to_attempted(outcome_id, actor="SEED_SCRIPT")

            # Record the final outcome
            outcome_str = scenario["outcome"]
            save_recovery_outcome(
                outcome_id=outcome_id,
                outcome=outcome_str,
                recovered_amount=float(scenario["recovered"]),
                recovery_time_seconds=scenario.get("time"),
                reason=scenario.get("reason", "Demo simulation record"),
                actor="SEED_SCRIPT"
            )

            seeded += 1

        except Exception as e:
            errors.append({"payment_id": scenario["payment_id"], "error": str(e)})

    return {
        "seeded": True,
        "records_added": seeded,
        "errors": errors,
        "existing_before_seed": existing_count,
        "message": f"Successfully seeded {seeded} SIMULATION recovery outcomes.",
        "note": "These are DEMO records only. No real payments were affected."
    }


if __name__ == "__main__":
    from typing import Dict, Any  # ensure import in __main__
    result = seed_recovery_outcomes()
    print("\n=== RecoverAI Demo Data Seeding ===")
    for k, v in result.items():
        if k != "errors":
            print(f"  {k}: {v}")
    if result.get("errors"):
        print(f"  errors: {result['errors']}")
    print("===================================\n")
