"""
RecoverAI Smart Alerts Automated Test Suite
Tests Smart Alert generation, priority rules, deduplication, lifecycle transitions,
revenue impact calculations, API endpoints, and regression coverage.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import (
    app,
    home,
    recover_payment,
    decisions as api_decisions,
    revenue_opportunities as api_revenue_opportunities,
    list_alerts as api_list_alerts,
    alerts_summary as api_alerts_summary,
    acknowledge_alert as api_acknowledge_alert,
    resolve_alert as api_resolve_alert,
    Payment
)
from src.smart_alerts import (
    SmartAlertConfig,
    calculate_alert_priority,
    calculate_alert_score,
    generate_alert_explanation,
    evaluate_decision_for_alerts,
    evaluate_system_alerts,
    build_alert_record
)
from src.database import (
    create_database,
    save_decision,
    get_decisions,
    save_alert,
    get_alerts,
    get_alert_by_id,
    acknowledge_alert_db,
    resolve_alert_db,
    get_alerts_summary_metrics,
    sync_smart_alerts
)


# ==============================================================================
# 1. Alert Generation & Priority Rule Tests
# ==============================================================================

def test_critical_alert_generation():
    """Verify that CRITICAL_OPPORTUNITY triggers with CRITICAL priority."""
    decision = {
        "payment_id": "PAY_CRIT_01",
        "customer_id": "CUST_01",
        "payment_amount": 25000.0,
        "recovery_probability": 0.92,
        "expected_revenue": 23000.0,
        "risk_level": "LOW",
        "recommended_action": "RETRY_PAYMENT",
        "revenue_opportunity_score": 94.5
    }
    alerts = evaluate_decision_for_alerts(decision)
    types = [a["alert_type"] for a in alerts]
    assert "CRITICAL_OPPORTUNITY" in types

    crit_raw = next(a for a in alerts if a["alert_type"] == "CRITICAL_OPPORTUNITY")
    record = build_alert_record(crit_raw)
    assert record["priority"] == "CRITICAL"
    assert record["amount"] == 25000.0
    assert "Critical" in record["title"]


def test_high_revenue_risk_alert_generation():
    """Verify that HIGH_REVENUE_RISK triggers for high-value high-risk payments."""
    decision = {
        "payment_id": "PAY_RISK_01",
        "customer_id": "CUST_02",
        "payment_amount": 35000.0,
        "recovery_probability": 0.20,
        "expected_revenue": 7000.0,
        "risk_level": "HIGH",
        "recommended_action": "CUSTOMER_ACTION_REQUIRED",
        "revenue_opportunity_score": 45.0
    }
    alerts = evaluate_decision_for_alerts(decision)
    types = [a["alert_type"] for a in alerts]
    assert "HIGH_REVENUE_RISK" in types
    assert "CUSTOMER_ACTION_REQUIRED" in types

    risk_raw = next(a for a in alerts if a["alert_type"] == "HIGH_REVENUE_RISK")
    record = build_alert_record(risk_raw)
    assert record["priority"] == "CRITICAL"  # Overridden because amount >= 10k
    assert "Revenue at Risk" in record["title"]


def test_low_recovery_probability_alert():
    """Verify that LOW_RECOVERY_PROBABILITY triggers when prob <= 40% and amount >= 3000."""
    decision = {
        "payment_id": "PAY_LOW_01",
        "customer_id": "CUST_03",
        "payment_amount": 5000.0,
        "recovery_probability": 0.15,
        "expected_revenue": 750.0,
        "risk_level": "HIGH",
        "recommended_action": "STOP_AUTOMATIC_RECOVERY",
        "revenue_opportunity_score": 22.0
    }
    alerts = evaluate_decision_for_alerts(decision)
    types = [a["alert_type"] for a in alerts]
    assert "LOW_RECOVERY_PROBABILITY" in types

    low_raw = next(a for a in alerts if a["alert_type"] == "LOW_RECOVERY_PROBABILITY")
    record = build_alert_record(low_raw)
    assert record["priority"] in ["MEDIUM", "HIGH"]


def test_retry_recommended_alert():
    """Verify that RETRY_RECOMMENDED triggers when prob >= 80% and action is RETRY_PAYMENT."""
    decision = {
        "payment_id": "PAY_RETRY_01",
        "customer_id": "CUST_04",
        "payment_amount": 4500.0,
        "recovery_probability": 0.88,
        "expected_revenue": 3960.0,
        "risk_level": "LOW",
        "recommended_action": "RETRY_PAYMENT",
        "revenue_opportunity_score": 68.0
    }
    alerts = evaluate_decision_for_alerts(decision)
    types = [a["alert_type"] for a in alerts]
    assert "RETRY_RECOMMENDED" in types


# ==============================================================================
# 2. Deduplication Tests
# ==============================================================================

def test_alert_deduplication():
    """Verify that inserting identical alert dedup_key does not create duplicates."""
    import uuid
    test_pid = f"PAY_DEDUP_{uuid.uuid4().hex[:6]}"
    raw = {
        "alert_type": "HIGH_REVENUE_RISK",
        "payment_id": test_pid,
        "customer_id": "CUST_DEDUP",
        "amount": 18000.0,
        "recovery_probability": 0.25,
        "risk_level": "HIGH",
        "opportunity_score": 40.0,
        "recommended_action": "STOP_AUTOMATIC_RECOVERY",
        "expected_recovery": 4500.0
    }
    rec1 = build_alert_record(raw)
    saved1 = save_alert(rec1)
    assert saved1 is True

    # Attempt to save duplicate
    rec2 = build_alert_record(raw)
    saved2 = save_alert(rec2)
    assert saved2 is False  # Deduplicated!


# ==============================================================================
# 3. Lifecycle Transitions & State Machine Tests
# ==============================================================================

def test_alert_lifecycle_and_invalid_transitions():
    """
    Test alert status lifecycle:
    OPEN -> ACKNOWLEDGED -> RESOLVED
    And ensure invalid transitions are rejected.
    """
    import uuid
    test_pid = f"PAY_LC_{uuid.uuid4().hex[:6]}"
    raw = {
        "alert_type": "CUSTOMER_ACTION_REQUIRED",
        "payment_id": test_pid,
        "customer_id": "CUST_LC",
        "amount": 22000.0,
        "recovery_probability": 0.30,
        "risk_level": "HIGH",
        "opportunity_score": 55.0,
        "recommended_action": "CUSTOMER_ACTION_REQUIRED",
        "expected_recovery": 6600.0
    }
    rec = build_alert_record(raw)
    saved = save_alert(rec)
    assert saved is True
    alert_id = rec["alert_id"]

    # 1. Verify initially OPEN
    alert_initial = get_alert_by_id(alert_id)
    assert alert_initial is not None
    assert alert_initial["status"] == "OPEN"

    # 2. Transition OPEN -> ACKNOWLEDGED
    ack_result = acknowledge_alert_db(alert_id)
    assert ack_result["status"] == "ACKNOWLEDGED"
    assert ack_result["acknowledged_at"] is not None

    # 3. Invalid Transition: Acknowledge an already ACKNOWLEDGED alert
    try:
        acknowledge_alert_db(alert_id)
        assert False, "Should raise ValueError for already acknowledged alert"
    except ValueError:
        pass

    # 4. Transition ACKNOWLEDGED -> RESOLVED
    res_result = resolve_alert_db(alert_id)
    assert res_result["status"] == "RESOLVED"
    assert res_result["resolved_at"] is not None

    # 5. Invalid Transition: Resolve an already RESOLVED alert
    try:
        resolve_alert_db(alert_id)
        assert False, "Should raise ValueError for already resolved alert"
    except ValueError:
        pass


# ==============================================================================
# 4. Revenue Impact & Summary Metrics
# ==============================================================================

def test_alerts_summary_and_revenue_impact():
    """Verify summary counts and financial impact calculations."""
    summary = get_alerts_summary_metrics()
    assert "total_alerts" in summary
    assert "open_alerts" in summary
    assert "revenue_at_risk" in summary
    assert "potential_recovery" in summary
    assert "critical_revenue_at_risk" in summary
    assert summary["revenue_at_risk"] >= 0.0


# ==============================================================================
# 5. API Endpoints Tests
# ==============================================================================

def test_api_alerts_endpoints():
    """Test GET /alerts and GET /alerts/summary handlers."""
    alerts = api_list_alerts()
    assert isinstance(alerts, list)

    summary = api_alerts_summary()
    assert "total_alerts" in summary
    assert summary["total_alerts"] == len(alerts)

    # Test filtering by status
    open_alerts = api_list_alerts(status="OPEN")
    for a in open_alerts:
        assert a["status"] == "OPEN"


def test_api_regression_endpoints():
    """Verify existing endpoints remain unbroken."""
    # 1. GET /
    h = home()
    assert h["status"] == "healthy"

    # 2. GET /decisions
    d = api_decisions()
    assert "total_decisions" in d

    # 3. GET /revenue-opportunities
    ro = api_revenue_opportunities()
    assert "total_opportunities" in ro

    # 4. POST /recover
    p = Payment(
        amount=14000.0,
        payment_method="card",
        failure_reason="network_timeout",
        previous_payments=12,
        previous_failures=1,
        days_since_last_payment=3,
        subscription=1,
        hour=16,
        is_weekend=0,
        payment_id="PAY_REGRESS_TEST"
    )
    rec_res = recover_payment(p)
    assert "revenue_opportunity_score" in rec_res
    assert "priority_level" in rec_res


# ==============================================================================
# Runner
# ==============================================================================

if __name__ == "__main__":
    test_functions = [
        ("Critical Alert Generation", test_critical_alert_generation),
        ("High Revenue Risk Alert Generation", test_high_revenue_risk_alert_generation),
        ("Low Recovery Probability Alert", test_low_recovery_probability_alert),
        ("Retry Recommended Alert", test_retry_recommended_alert),
        ("Alert Deduplication", test_alert_deduplication),
        ("Alert Lifecycle & Invalid Transitions", test_alert_lifecycle_and_invalid_transitions),
        ("Alerts Summary & Revenue Impact", test_alerts_summary_and_revenue_impact),
        ("API Alerts Endpoints", test_api_alerts_endpoints),
        ("Regression Endpoints (Home, Decisions, Opportunities, Recover)", test_api_regression_endpoints)
    ]

    print("=" * 60)
    print("           RECOVERAI SMART ALERTS TEST SUITE")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, func in test_functions:
        try:
            func()
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as ae:
            print(f"FAIL: {name} -> Assertion failed: {ae}")
            failed += 1
        except Exception as e:
            print(f"FAIL: {name} -> Error: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed.")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
