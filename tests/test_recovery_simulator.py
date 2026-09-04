"""
RecoverAI Recovery Simulator Automated Test Suite
Tests what-if simulation, strategy evaluation, Recovery Agent safety rule enforcement,
scenario comparisons, sensitivity analysis, simulation history persistence, and API endpoints.
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
    simulate_recovery as api_simulate_recovery,
    list_simulations as api_list_simulations,
    get_single_simulation as api_get_single_simulation,
    SimulationRequest,
    Payment
)
from src.recovery_simulator import (
    run_recovery_simulation,
    evaluate_all_strategies,
    determine_best_strategy,
    compare_scenarios,
    generate_sensitivity_analysis,
    generate_failure_reason_matrix,
    STRATEGY_NAMES
)
from src.database import (
    create_database,
    save_simulation,
    get_simulations,
    get_simulation_by_id
)


# ==============================================================================
# 1. Simulator Core & Strategy Evaluation Tests
# ==============================================================================

def test_valid_transient_simulation():
    """Verify simulation for transient failure (network_timeout) allows AUTOMATIC_RETRY."""
    payment = {
        "amount": 5000.0,
        "payment_method": "card",
        "failure_reason": "network_timeout",
        "previous_payments": 10,
        "previous_failures": 1,
        "days_since_last_payment": 3,
        "subscription": 1,
        "hour": 14,
        "is_weekend": 0
    }
    result = run_recovery_simulation(payment, selected_strategy="AUTOMATIC_RETRY")
    assert result["strategy"] == "AUTOMATIC_RETRY"
    assert result["strategy_allowed"] is True
    assert result["recovery_probability"] > 0.50
    assert result["expected_recovery"] > 0.0
    assert result["revenue_at_risk"] == 5000.0
    assert len(result["strategy_comparisons"]) == 5
    assert "explanation" in result
    assert "key_factors" in result


def test_safety_rule_enforcement_permanent_decline():
    """Verify that permanent failure (bank_decline) blocks AUTOMATIC_RETRY and recommends CUSTOMER_ACTION."""
    payment = {
        "amount": 12000.0,
        "payment_method": "card",
        "failure_reason": "bank_decline",
        "previous_payments": 5,
        "previous_failures": 2,
        "days_since_last_payment": 10,
        "subscription": 0,
        "hour": 16,
        "is_weekend": 0
    }
    result = run_recovery_simulation(payment, selected_strategy="AUTOMATIC_RETRY")
    # Automatic retry MUST be blocked by safety rules
    assert result["strategy_allowed"] is False
    assert result["risk_level"] == "HIGH"
    assert "Blocked" in result["safety_note"]
    assert result["best_strategy"] in ["CUSTOMER_ACTION", "PAYMENT_METHOD_CHANGE"]


def test_all_strategies_evaluation_matrix():
    """Verify that all 5 strategies are evaluated with valid metrics."""
    payment = {
        "amount": 8000.0,
        "payment_method": "card",
        "failure_reason": "insufficient_balance",
        "previous_payments": 8,
        "previous_failures": 1,
        "days_since_last_payment": 4,
        "subscription": 1
    }
    strategies = evaluate_all_strategies(payment)
    assert len(strategies) == 5
    names = [s["strategy"] for s in strategies]
    for s_name in STRATEGY_NAMES:
        assert s_name in names

    # Verify NO_ACTION produces 0 expected recovery
    no_act = next(s for s in strategies if s["strategy"] == "NO_ACTION")
    assert no_act["expected_recovery"] == 0.0
    assert no_act["recovery_probability"] == 0.0


def test_best_strategy_determination():
    """Verify that determine_best_strategy selects an allowed strategy maximizing expected recovery."""
    payment = {
        "amount": 15000.0,
        "payment_method": "card",
        "failure_reason": "expired_card",
        "previous_payments": 12,
        "previous_failures": 0,
        "days_since_last_payment": 2,
        "subscription": 1
    }
    strategies = evaluate_all_strategies(payment)
    best = determine_best_strategy(strategies)
    assert best["strategy_allowed"] is True
    assert best["strategy"] != "AUTOMATIC_RETRY"  # Blocked on expired card
    assert best["expected_recovery"] > 0.0


# ==============================================================================
# 2. Scenario Comparison & Sensitivity Tests
# ==============================================================================

def test_scenario_comparison():
    """Verify comparative analysis between Scenario A and Scenario B."""
    scenario_a = {
        "amount": 10000.0,
        "payment_method": "card",
        "failure_reason": "network_timeout",
        "previous_payments": 15,
        "previous_failures": 0,
        "days_since_last_payment": 1,
        "subscription": 1,
        "strategy": "AUTOMATIC_RETRY"
    }
    scenario_b = {
        "amount": 10000.0,
        "payment_method": "card",
        "failure_reason": "bank_decline",
        "previous_payments": 2,
        "previous_failures": 4,
        "days_since_last_payment": 30,
        "subscription": 0,
        "strategy": "AUTOMATIC_RETRY"
    }
    comp = compare_scenarios(scenario_a, scenario_b)
    assert "winner" in comp
    assert comp["winner"] == "Scenario A"
    assert comp["expected_recovery_diff"] > 0.0
    assert "verdict" in comp


def test_sensitivity_analysis():
    """Verify sensitivity calculations across stepped transaction amounts."""
    payment = {
        "payment_method": "card",
        "failure_reason": "network_timeout",
        "previous_payments": 8,
        "previous_failures": 1,
        "days_since_last_payment": 5,
        "subscription": 1
    }
    amounts = [1000.0, 5000.0, 10000.0, 25000.0, 50000.0]
    results = generate_sensitivity_analysis(payment, amounts=amounts)
    assert len(results) == 5
    for r in results:
        assert r["expected_recovery"] == round(r["amount"] * r["recovery_probability"], 2)


def test_failure_reason_matrix():
    """Verify cross-comparison across all failure reasons."""
    payment = {
        "amount": 10000.0,
        "payment_method": "card",
        "previous_payments": 10,
        "previous_failures": 1,
        "days_since_last_payment": 3,
        "subscription": 1
    }
    matrix = generate_failure_reason_matrix(payment)
    assert len(matrix) == 6
    reasons = [m["failure_reason"] for m in matrix]
    assert "network_timeout" in reasons
    assert "bank_decline" in reasons


# ==============================================================================
# 3. Database Persistence & API Endpoints Tests
# ==============================================================================

def test_simulation_database_persistence():
    """Verify saving and retrieving simulation history from SQLite."""
    payment = {
        "amount": 7500.0,
        "payment_method": "upi",
        "failure_reason": "technical_error",
        "previous_payments": 6,
        "previous_failures": 1,
        "days_since_last_payment": 4,
        "subscription": 1
    }
    sim_res = run_recovery_simulation(payment, selected_strategy="AUTOMATIC_RETRY")
    sim_id = save_simulation(sim_res)
    assert sim_id.startswith("SIM-")

    fetched = get_simulation_by_id(sim_id)
    assert fetched is not None
    assert fetched["simulation_id"] == sim_id
    assert fetched["amount"] == 7500.0

    all_sims = get_simulations(limit=10)
    assert len(all_sims) > 0
    assert any(s["simulation_id"] == sim_id for s in all_sims)


def test_api_simulate_recovery():
    """Verify POST /simulate-recovery API endpoint."""
    req = SimulationRequest(
        amount=6000.0,
        payment_method="card",
        failure_reason="network_timeout",
        previous_payments=8,
        previous_failures=1,
        days_since_last_payment=2,
        subscription=1,
        strategy="AUTOMATIC_RETRY"
    )
    api_res = api_simulate_recovery(req)
    assert api_res["simulation_id"].startswith("SIM-")
    assert api_res["expected_recovery"] > 0.0
    assert api_res["strategy_allowed"] is True

    # Test GET /simulations
    sims_list = api_list_simulations(limit=5)
    assert "total_simulations" in sims_list
    assert len(sims_list["simulations"]) > 0

    # Test GET /simulations/{id}
    single = api_get_single_simulation(api_res["simulation_id"])
    assert single["simulation_id"] == api_res["simulation_id"]


def test_regression_endpoints():
    """Verify existing endpoints remain functional."""
    # 1. GET /
    h = home()
    assert h["status"] == "healthy"

    # 2. GET /decisions
    d = api_decisions()
    assert "total_decisions" in d

    # 3. GET /revenue-opportunities
    ro = api_revenue_opportunities()
    assert "total_opportunities" in ro

    # 4. GET /alerts and summary
    alerts = api_list_alerts()
    assert isinstance(alerts, list)
    summary = api_alerts_summary()
    assert "total_alerts" in summary

    # 5. POST /recover
    p = Payment(
        amount=15000.0,
        payment_method="card",
        failure_reason="network_timeout",
        previous_payments=10,
        previous_failures=1,
        days_since_last_payment=2,
        subscription=1,
        payment_id="PAY_SIM_REGRESS"
    )
    rec = recover_payment(p)
    assert "recovery_probability" in rec
    assert "revenue_opportunity_score" in rec


# ==============================================================================
# Runner
# ==============================================================================

if __name__ == "__main__":
    test_functions = [
        ("Valid Transient Simulation", test_valid_transient_simulation),
        ("Safety Rule Enforcement on Permanent Decline", test_safety_rule_enforcement_permanent_decline),
        ("All Strategies Evaluation Matrix", test_all_strategies_evaluation_matrix),
        ("Best Strategy Determination", test_best_strategy_determination),
        ("Scenario Comparison (A vs B)", test_scenario_comparison),
        ("Amount Sensitivity Analysis", test_sensitivity_analysis),
        ("Failure Reason Matrix", test_failure_reason_matrix),
        ("Simulation Database Persistence", test_simulation_database_persistence),
        ("API /simulate-recovery and /simulations", test_api_simulate_recovery),
        ("Regression Endpoints (Home, Decisions, Opps, Alerts, Recover)", test_regression_endpoints)
    ]

    print("=" * 60)
    print("        RECOVERAI RECOVERY SIMULATOR TEST SUITE")
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
