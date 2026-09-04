"""
RecoverAI Comprehensive Test Suite
Tests Intelligent Revenue Opportunity Ranking, Priority Classification,
Safety Rule Supremacy, Database Persistence, and FastAPI Endpoints.
"""

import sys
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import (
    app,
    home,
    recover_payment,
    decisions as api_decisions,
    revenue_opportunities as api_revenue_opportunities,
    decision_explanation as api_decision_explanation,
    Payment
)
from src.ranking_engine import (
    calculate_opportunity_score,
    classify_priority_level,
    generate_opportunity_explanation,
    rank_opportunities
)
from src.recovery_agent import recovery_agent
from src.database import (
    create_database,
    save_decision,
    get_decisions,
    get_recovery_opportunities
)


# ==============================================================================
# 1. Ranking Engine & Score Boundary Tests
# ==============================================================================

def test_score_boundaries():
    """Verify that opportunity scores always stay strictly within [0.0, 100.0]."""
    test_cases = [
        # (amount, prob, exp_rev, action, reason)
        (0.0, 0.0, 0.0, "STOP_AUTOMATIC_RECOVERY", "bank_decline"),
        (100000.0, 1.0, 100000.0, "RETRY_PAYMENT", "network_timeout"),
        (500.0, 0.5, 250.0, "SCHEDULE_RETRY", "insufficient_balance"),
        (-100.0, -0.5, -50.0, "STOP_AUTOMATIC_RECOVERY", "unknown"),
        (1000000.0, 1.5, 1500000.0, "RETRY_PAYMENT", "network_timeout")
    ]
    for amt, prob, exp_rev, action, reason in test_cases:
        res = calculate_opportunity_score(
            payment_amount=amt,
            recovery_probability=prob,
            expected_revenue=exp_rev,
            recommended_action=action,
            failure_reason=reason
        )
        score = res["revenue_opportunity_score"]
        assert 0.0 <= score <= 100.0, f"Score {score} out of bounds for inputs {(amt, prob, exp_rev, action)}"


def test_priority_tier_classification():
    """Verify exact priority level categories."""
    assert classify_priority_level(95.0) == "CRITICAL"
    assert classify_priority_level(90.0) == "CRITICAL"
    assert classify_priority_level(89.9) == "HIGH"
    assert classify_priority_level(75.0) == "HIGH"
    assert classify_priority_level(74.9) == "MEDIUM"
    assert classify_priority_level(50.0) == "MEDIUM"
    assert classify_priority_level(49.9) == "LOW"
    assert classify_priority_level(25.0) == "LOW"
    assert classify_priority_level(24.9) == "VERY LOW"
    assert classify_priority_level(0.0) == "VERY LOW"


def test_high_value_high_probability_opportunity():
    """
    Test Case 1: High-value + high-probability payment (e.g., ₹15,000, 91% prob).
    Should receive a very high score (CRITICAL / HIGH priority).
    """
    res = calculate_opportunity_score(
        payment_amount=15000.0,
        recovery_probability=0.91,
        expected_revenue=13650.0,
        recommended_action="RETRY_PAYMENT",
        failure_reason="network_timeout",
        customer_info={"previous_payments": 15, "subscription": 1},
        retry_count=0
    )
    score = res["revenue_opportunity_score"]
    priority = res["priority_level"]
    assert score >= 85.0, f"Expected score >= 85, got {score}"
    assert priority in ["CRITICAL", "HIGH"], f"Expected CRITICAL or HIGH, got {priority}"
    assert "High-value" in res["explanation"] or "priority" in res["explanation"].lower()


def test_low_value_vs_high_value_opportunity():
    """
    Test Case 2: Compare Low-value (₹2,000, 98% prob) vs High-value (₹10,000, 90% prob).
    High-value payment should produce a higher opportunity score because recoverable revenue is much larger.
    """
    # Payment A: ₹10,000, 90% -> expected ₹9,000
    res_a = calculate_opportunity_score(
        payment_amount=10000.0,
        recovery_probability=0.90,
        expected_revenue=9000.0,
        recommended_action="RETRY_PAYMENT",
        failure_reason="network_timeout"
    )

    # Payment B: ₹2,000, 98% -> expected ₹1,960
    res_b = calculate_opportunity_score(
        payment_amount=2000.0,
        recovery_probability=0.98,
        expected_revenue=1960.0,
        recommended_action="RETRY_PAYMENT",
        failure_reason="network_timeout"
    )

    assert res_a["revenue_opportunity_score"] > res_b["revenue_opportunity_score"]


def test_high_value_low_probability_opportunity():
    """
    Test Case 3: High-value + low-probability payment (e.g., ₹50,000, 15% prob).
    Low model confidence should drag down the score.
    """
    res_low_prob = calculate_opportunity_score(
        payment_amount=50000.0,
        recovery_probability=0.15,
        expected_revenue=7500.0,
        recommended_action="STOP_AUTOMATIC_RECOVERY",
        failure_reason="technical_error"
    )

    res_high_prob = calculate_opportunity_score(
        payment_amount=15000.0,
        recovery_probability=0.90,
        expected_revenue=13500.0,
        recommended_action="RETRY_PAYMENT",
        failure_reason="network_timeout"
    )

    assert res_low_prob["revenue_opportunity_score"] < res_high_prob["revenue_opportunity_score"]


def test_safety_rule_supremacy_and_explanation():
    """
    Test Case 4: Safety rules must strictly override revenue ranking.
    Permanent failures (bank_decline, authentication_failed, expired_card) must remain
    CUSTOMER_ACTION_REQUIRED even if payment is ₹50,000.
    """
    payment = {
        "payment_id": "PAY_TEST_BANK",
        "customer_id": "CUST_TEST",
        "amount": 50000.0,
        "payment_method": "card",
        "failure_reason": "bank_decline",
        "previous_payments": 20,
        "previous_failures": 0,
        "days_since_last_payment": 2,
        "subscription": 1,
        "hour": 14,
        "is_weekend": 0
    }
    decision = recovery_agent(payment)

    assert decision["recommended_action"] == "CUSTOMER_ACTION_REQUIRED"
    assert decision["risk_level"] == "HIGH"
    assert "Safety rules strictly prohibit" in decision["explanation"] or "Requires customer intervention" in decision["explanation"]


def test_ranking_order_descending():
    """
    Test Case 6: Verify rank_opportunities sorts descending by score and assigns rank 1 to highest score.
    """
    items = [
        {"payment_id": "P1", "revenue_opportunity_score": 45.0},
        {"payment_id": "P2", "revenue_opportunity_score": 92.5},
        {"payment_id": "P3", "revenue_opportunity_score": 78.0},
    ]
    ranked = rank_opportunities(items, sort_by="revenue_opportunity_score", sort_order="desc")

    assert ranked[0]["payment_id"] == "P2"
    assert ranked[0]["priority_rank"] == 1
    assert ranked[1]["payment_id"] == "P3"
    assert ranked[1]["priority_rank"] == 2
    assert ranked[2]["payment_id"] == "P1"
    assert ranked[2]["priority_rank"] == 3


# ==============================================================================
# 2. FastAPI Endpoints & Integration Tests
# ==============================================================================

def test_api_home():
    """Regression test for GET /"""
    data = home()
    assert data["status"] == "healthy"
    assert "RecoverAI API" in data["message"]


def test_api_recover_payment():
    """Regression test for POST /recover"""
    payload = Payment(
        amount=12500.0,
        payment_method="card",
        failure_reason="network_timeout",
        previous_payments=10,
        previous_failures=1,
        days_since_last_payment=4,
        subscription=1,
        hour=15,
        is_weekend=0,
        payment_id="PAY_API_TEST",
        customer_id="CUST_API_TEST"
    )
    data = recover_payment(payload)
    assert "revenue_opportunity_score" in data
    assert "priority_level" in data
    assert "expected_revenue" in data
    assert data["payment_amount"] == 12500.0
    assert data["payment_id"] == "PAY_API_TEST"


def test_api_decisions_history():
    """Regression test for GET /decisions"""
    data = api_decisions()
    assert "total_decisions" in data
    assert "decisions" in data
    assert isinstance(data["decisions"], list)
    assert data["total_decisions"] >= 1


def test_api_revenue_opportunities_endpoint():
    """
    Test GET /revenue-opportunities endpoint with various query filters and limit.
    """
    # 1. Base query
    data = api_revenue_opportunities()
    assert "total_opportunities" in data
    assert "opportunities" in data
    assert isinstance(data["opportunities"], list)

    if data["total_opportunities"] > 0:
        first = data["opportunities"][0]
        assert "priority_rank" in first
        assert "payment_id" in first
        assert "revenue_opportunity_score" in first
        assert "priority_level" in first
        assert "explanation" in first
        assert first["priority_rank"] == 1

    # 2. Test Limit
    data_limit = api_revenue_opportunities(limit=2)
    assert len(data_limit["opportunities"]) <= 2

    # 3. Test Filter by Priority Level
    data_prio = api_revenue_opportunities(priority_level="CRITICAL")
    for opp in data_prio["opportunities"]:
        assert opp["priority_level"] == "CRITICAL"

    # 4. Test Filter by Risk Level
    data_risk = api_revenue_opportunities(risk_level="LOW")
    for opp in data_risk["opportunities"]:
        assert opp["risk_level"] == "LOW"

    # 5. Test Filter by Failure Reason
    data_fr = api_revenue_opportunities(failure_reason="network_timeout")
    for opp in data_fr["opportunities"]:
        assert opp["failure_reason"] == "network_timeout"


def test_api_decision_explanation():
    """Regression test for GET /decisions/{id}/explanation"""
    data_all = api_decisions()
    decisions = data_all.get("decisions", [])
    if decisions:
        dec_id = decisions[0]["id"]
        data_exp = api_decision_explanation(dec_id)
        assert "explanation" in data_exp
        assert data_exp["decision_id"] == dec_id


if __name__ == "__main__":
    test_functions = [
        ("Score Boundaries Test", test_score_boundaries),
        ("Priority Classification Test", test_priority_tier_classification),
        ("High-Value + High-Probability Opportunity", test_high_value_high_probability_opportunity),
        ("Low-Value vs High-Value Comparison", test_low_value_vs_high_value_opportunity),
        ("High-Value + Low-Probability Opportunity", test_high_value_low_probability_opportunity),
        ("Safety Rule Supremacy & Override", test_safety_rule_supremacy_and_explanation),
        ("Ranking Order Descending", test_ranking_order_descending),
        ("API GET / Home Endpoint", test_api_home),
        ("API POST /recover Endpoint", test_api_recover_payment),
        ("API GET /decisions Endpoint", test_api_decisions_history),
        ("API GET /revenue-opportunities Endpoint", test_api_revenue_opportunities_endpoint),
        ("API GET /decisions/{id}/explanation Endpoint", test_api_decision_explanation)
    ]

    print("=" * 60)
    print("      RECOVERAI OPPORTUNITY RANKING TEST SUITE")
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
