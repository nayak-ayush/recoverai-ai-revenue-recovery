"""
RecoverAI Recovery Simulator Engine
Provides what-if decision support and strategy modeling for failed payments.
Simulates recovery strategies:
  1. AUTOMATIC_RETRY
  2. CUSTOMER_ACTION
  3. PAYMENT_METHOD_CHANGE
  4. WAIT_AND_RETRY
  5. NO_ACTION
Strictly enforces Recovery Agent safety rules without executing real payment transactions.
"""

import sys
import uuid
import onnxruntime as ort
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Setup path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ranking_engine import calculate_opportunity_score, classify_priority_level
from src.recovery_agent import recovery_agent

MODEL_FILE = PROJECT_ROOT / "models" / "recovery_model.onnx"
try:
    model = ort.InferenceSession(str(MODEL_FILE), providers=["CPUExecutionProvider"])
except Exception:
    model = None


# ==============================================================================
# 1. Strategy Definitions & Metadata
# ==============================================================================

STRATEGY_NAMES = [
    "AUTOMATIC_RETRY",
    "CUSTOMER_ACTION",
    "PAYMENT_METHOD_CHANGE",
    "WAIT_AND_RETRY",
    "NO_ACTION"
]

STRATEGY_DISPLAY_MAP = {
    "AUTOMATIC_RETRY": "Automatic Retry",
    "CUSTOMER_ACTION": "Customer Action",
    "PAYMENT_METHOD_CHANGE": "Payment Method Change",
    "WAIT_AND_RETRY": "Wait & Retry",
    "NO_ACTION": "No Action"
}

PERMANENT_FAILURES = [
    "bank_decline",
    "authentication_failed",
    "expired_card"
]

VALID_FAILURE_REASONS = [
    "network_timeout",
    "technical_error",
    "insufficient_balance",
    "authentication_failed",
    "expired_card",
    "bank_decline"
]

VALID_PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet"]


# ==============================================================================
# 2. Base Model Prediction Helper
# ==============================================================================

def predict_raw_probability(payment_data: Dict[str, Any]) -> float:
    """Run model prediction on payment dictionary features."""
    if model is None:
        return 0.50

    features_dict = {
        "amount": float(payment_data.get("amount", 5000.0)),
        "payment_method": str(payment_data.get("payment_method", "card")).lower(),
        "failure_reason": str(payment_data.get("failure_reason", "network_timeout")).lower(),
        "previous_payments": int(payment_data.get("previous_payments", 0)),
        "previous_failures": int(payment_data.get("previous_failures", 0)),
        "days_since_last_payment": int(payment_data.get("days_since_last_payment", 0)),
        "subscription": int(payment_data.get("subscription", 0)),
        "hour": int(payment_data.get("hour", 12)),
        "is_weekend": int(payment_data.get("is_weekend", 0))
    }
    inputs = {
        "amount": [[float(payment_data.get("amount", 0.0))]],
        "payment_method": [[payment_data.get("payment_method", "card")]],
        "failure_reason": [[payment_data.get("failure_reason", "network_timeout")]],
        "previous_payments": [[float(payment_data.get("previous_payments", 0))]],
        "previous_failures": [[float(payment_data.get("previous_failures", 0))]],
        "days_since_last_payment": [[float(payment_data.get("days_since_last_payment", 0))]],
        "subscription": [[float(payment_data.get("subscription", 0))]],
        "hour": [[float(payment_data.get("hour", 12))]],
        "is_weekend": [[float(payment_data.get("is_weekend", 0))]],
    }
    outputs = model.run(None, inputs)
    probability_map = outputs[1][0]
    prob = float(probability_map[1])
    return max(0.0, min(1.0, prob))


# ==============================================================================
# 3. Strategy Evaluation Logic
# ==============================================================================

def evaluate_strategy_outcome(
    payment_data: Dict[str, Any],
    strategy: str,
    base_prob: float,
    base_action: str,
    base_risk: str
) -> Dict[str, Any]:
    """
    Evaluate a specific recovery strategy for a given payment scenario.
    Calculates strategy-specific probability, expected recovery, risk, opportunity score,
    and whether the strategy is allowed under Recovery Agent safety rules.
    """
    amount = float(payment_data.get("amount", 0.0))
    failure_reason = str(payment_data.get("failure_reason", "network_timeout")).lower()
    method = str(payment_data.get("payment_method", "card")).lower()
    strategy = str(strategy).upper()
    is_permanent = failure_reason in PERMANENT_FAILURES

    if strategy == "AUTOMATIC_RETRY":
        if is_permanent:
            # SAFETY RULE: Permanent failure cannot be automatically retried
            strategy_allowed = False
            sim_prob = max(0.05, round(base_prob * 0.15, 4))
            risk_level = "HIGH"
            recommended_action = "CUSTOMER_ACTION_REQUIRED"
            safety_note = (
                f"Blocked: Automatic retry is prohibited for '{failure_reason}'. "
                f"Repeated retries cause customer friction and gateway penalties."
            )
        else:
            strategy_allowed = True
            sim_prob = round(base_prob, 4)
            risk_level = "LOW" if sim_prob >= 0.75 else ("MEDIUM" if sim_prob >= 0.50 else "HIGH")
            recommended_action = "RETRY_PAYMENT"
            safety_note = "Allowed: Transient failure eligible for instant automated secondary retry."

    elif strategy == "CUSTOMER_ACTION":
        strategy_allowed = True
        if is_permanent:
            # Customer action (updating card, approving in banking app) is the optimal path
            sim_prob = max(0.68, round(base_prob + 0.35, 4))
            sim_prob = min(0.85, sim_prob)
            risk_level = "MEDIUM"
            recommended_action = "CUSTOMER_ACTION_REQUIRED"
            safety_note = "Optimal for permanent declines: Customer updates card details or approves 2FA."
        else:
            sim_prob = round(base_prob * 0.85, 4)  # Minor drop due to customer response friction
            risk_level = "MEDIUM"
            recommended_action = "SEND_PAYMENT_REMINDER"
            safety_note = "Allowed: Customer payment link notification dispatched."

    elif strategy == "PAYMENT_METHOD_CHANGE":
        strategy_allowed = True
        # Simulate switching payment method to UPI or Netbanking
        alt_method = "upi" if method == "card" else "card"
        alt_payment = dict(payment_data)
        alt_payment["payment_method"] = alt_method
        alt_prob = predict_raw_probability(alt_payment)
        
        # If card failure, switching to UPI bypasses card-level issuer locks
        sim_prob = max(0.72, round(alt_prob * 1.05, 4)) if is_permanent else round(alt_prob, 4)
        sim_prob = min(0.92, sim_prob)
        risk_level = "LOW" if sim_prob >= 0.70 else "MEDIUM"
        recommended_action = "SEND_PAYMENT_REMINDER"
        safety_note = f"Allowed: Prompts customer to switch payment method from {method.upper()} to {alt_method.upper()}."

    elif strategy == "WAIT_AND_RETRY":
        if is_permanent:
            strategy_allowed = False
            sim_prob = max(0.05, round(base_prob * 0.10, 4))
            risk_level = "HIGH"
            recommended_action = "CUSTOMER_ACTION_REQUIRED"
            safety_note = f"Blocked: Delaying will not resolve permanent decline '{failure_reason}'."
        else:
            strategy_allowed = True
            # For insufficient balance or network timeouts, cool-down improves odds
            boost = 1.10 if failure_reason in ["insufficient_balance", "network_timeout"] else 1.0
            sim_prob = min(0.90, round(base_prob * boost, 4))
            risk_level = "MEDIUM" if sim_prob >= 0.60 else "HIGH"
            recommended_action = "SCHEDULE_RETRY"
            safety_note = "Allowed: Delaying retry to off-peak or after cool-down period."

    elif strategy == "NO_ACTION":
        strategy_allowed = True
        sim_prob = 0.0
        risk_level = "LOW"
        recommended_action = "STOP_AUTOMATIC_RECOVERY"
        safety_note = "Allowed: Recovery aborted to prevent gateway fees and operational costs."

    else:
        # Default fallback
        strategy_allowed = True
        sim_prob = round(base_prob, 4)
        risk_level = base_risk
        recommended_action = base_action
        safety_note = "Standard evaluation."

    expected_recovery = round(amount * sim_prob, 2)
    revenue_at_risk = round(amount, 2)

    # Calculate Opportunity Score for this simulated outcome
    opp_result = calculate_opportunity_score(
        payment_amount=amount,
        recovery_probability=sim_prob,
        expected_revenue=expected_recovery,
        recommended_action=recommended_action,
        failure_reason=failure_reason,
        customer_info={
            "previous_payments": payment_data.get("previous_payments", 0),
            "previous_failures": payment_data.get("previous_failures", 0),
            "subscription": payment_data.get("subscription", 0)
        }
    )

    opp_score = opp_result["revenue_opportunity_score"] if strategy != "NO_ACTION" else 0.0

    return {
        "strategy": strategy,
        "display_name": STRATEGY_DISPLAY_MAP.get(strategy, strategy),
        "recovery_probability": round(sim_prob, 4),
        "recovery_percentage": round(sim_prob * 100.0, 2),
        "expected_recovery": expected_recovery,
        "revenue_at_risk": revenue_at_risk,
        "risk_level": risk_level,
        "opportunity_score": round(opp_score, 1),
        "recommended_action": recommended_action,
        "strategy_allowed": strategy_allowed,
        "safety_note": safety_note
    }


# ==============================================================================
# 4. Comprehensive Strategy Matrix & Best Strategy Finder
# ==============================================================================

def evaluate_all_strategies(payment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluate all 5 strategies for the given payment scenario.
    Returns a list of strategy outcomes sorted by expected recovery descending.
    """
    base_prob = predict_raw_probability(payment_data)
    agent_result = recovery_agent(payment_data)
    base_action = agent_result.get("recommended_action", "STOP_AUTOMATIC_RECOVERY")
    base_risk = agent_result.get("risk_level", "MEDIUM")

    strategies_outcomes = []
    for strat in STRATEGY_NAMES:
        outcome = evaluate_strategy_outcome(
            payment_data=payment_data,
            strategy=strat,
            base_prob=base_prob,
            base_action=base_action,
            base_risk=base_risk
        )
        strategies_outcomes.append(outcome)

    return strategies_outcomes


def determine_best_strategy(strategies_outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Identifies the best allowable recovery strategy based on maximum expected recovery
    and opportunity score within safety rule constraints.
    """
    allowed = [s for s in strategies_outcomes if s["strategy_allowed"]]
    if not allowed:
        return strategies_outcomes[-1]  # NO_ACTION

    # Sort by expected_recovery descending, then opportunity_score descending
    best = sorted(allowed, key=lambda s: (s["expected_recovery"], s["opportunity_score"]), reverse=True)[0]
    return best


# ==============================================================================
# 5. Core Simulation Runner & Explanation Generator
# ==============================================================================

def run_recovery_simulation(
    payment_data: Dict[str, Any],
    selected_strategy: str = "AUTOMATIC_RETRY"
) -> Dict[str, Any]:
    """
    Execute full what-if recovery simulation for a transaction and strategy.
    Includes:
      - Selected strategy evaluation
      - Full 5-strategy comparison matrix
      - 🏆 Best strategy determination
      - Revenue impact metrics
      - AI explanation and key factors
    """
    amount = float(payment_data.get("amount", 0.0))
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    strategy_clean = str(selected_strategy).upper()
    if strategy_clean not in STRATEGY_NAMES:
        strategy_clean = "AUTOMATIC_RETRY"

    # 1. Base Agent Evaluation
    agent_decision = recovery_agent(payment_data)
    base_prob = agent_decision["recovery_probability"]
    base_action = agent_decision["recommended_action"]
    base_risk = agent_decision["risk_level"]

    # 2. Evaluate Selected Strategy
    selected_eval = evaluate_strategy_outcome(
        payment_data=payment_data,
        strategy=strategy_clean,
        base_prob=base_prob,
        base_action=base_action,
        base_risk=base_risk
    )

    # 3. Evaluate All Strategies
    all_strategies = evaluate_all_strategies(payment_data)

    # 4. Best Strategy Determination
    best_strat = determine_best_strategy(all_strategies)

    # 5. Revenue Impact Summary
    revenue_at_risk = amount
    expected_recovery = selected_eval["expected_recovery"]
    potential_recovery = best_strat["expected_recovery"]
    potential_improvement = round(max(0.0, potential_recovery - expected_recovery), 2)

    # 6. Generate AI Simulation Explanation
    explanation_text, key_factors = generate_simulation_explanation(
        payment_data=payment_data,
        selected_eval=selected_eval,
        best_strat=best_strat,
        base_decision=agent_decision
    )

    simulation_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"

    return {
        "simulation_id": simulation_id,
        "created_at": datetime.now().isoformat(),
        "amount": amount,
        "payment_method": payment_data.get("payment_method", "card"),
        "failure_reason": payment_data.get("failure_reason", "network_timeout"),
        "strategy": strategy_clean,
        "strategy_display_name": STRATEGY_DISPLAY_MAP.get(strategy_clean, strategy_clean),
        "recovery_probability": selected_eval["recovery_probability"],
        "recovery_percentage": selected_eval["recovery_percentage"],
        "expected_recovery": expected_recovery,
        "revenue_at_risk": revenue_at_risk,
        "potential_recovery": potential_recovery,
        "potential_improvement": potential_improvement,
        "risk_level": selected_eval["risk_level"],
        "opportunity_score": selected_eval["opportunity_score"],
        "recommended_action": selected_eval["recommended_action"],
        "strategy_allowed": selected_eval["strategy_allowed"],
        "safety_note": selected_eval["safety_note"],
        "best_strategy": best_strat["strategy"],
        "best_strategy_display": best_strat["display_name"],
        "best_expected_recovery": best_strat["expected_recovery"],
        "best_recovery_probability": best_strat["recovery_probability"],
        "explanation": explanation_text,
        "key_factors": key_factors,
        "strategy_comparisons": all_strategies
    }


def generate_simulation_explanation(
    payment_data: Dict[str, Any],
    selected_eval: Dict[str, Any],
    best_strat: Dict[str, Any],
    base_decision: Dict[str, Any]
) -> tuple[str, List[Dict[str, str]]]:
    """
    Generate transparent, human-readable AI explanation narrative and key factor breakdowns.
    """
    strat = selected_eval["strategy"]
    strat_name = selected_eval["display_name"]
    amount = float(payment_data.get("amount", 0.0))
    prob_pct = selected_eval["recovery_percentage"]
    exp_rev = selected_eval["expected_recovery"]
    reason = str(payment_data.get("failure_reason", "network_timeout"))
    is_allowed = selected_eval["strategy_allowed"]
    best_name = best_strat["display_name"]

    if not is_allowed:
        narrative = (
            f"⚠️ Strategy '{strat_name}' is BLOCKED by Recovery Agent safety rules for failure reason '{reason}'. "
            f"Retrying a hard/permanent decline wastes gateway costs and creates customer friction. "
            f"The AI recommends '{best_name}' instead, which delivers an expected recovery of ₹{best_strat['expected_recovery']:,.2f}."
        )
    elif strat == best_strat["strategy"]:
        narrative = (
            f"🏆 '{strat_name}' is currently the OPTIMAL strategy. "
            f"With a predicted recovery probability of {prob_pct:.1f}%, it yields an estimated ₹{exp_rev:,.2f} "
            f"recoverable revenue from the ₹{amount:,.2f} transaction while adhering to all safety constraints."
        )
    else:
        narrative = (
            f"'{strat_name}' is allowed and yields ₹{exp_rev:,.2f} ({prob_pct:.1f}% recovery probability). "
            f"However, '{best_name}' is stronger and could yield an additional ₹{best_strat['expected_recovery'] - exp_rev:,.2f} "
            f"(Total ₹{best_strat['expected_recovery']:,.2f})."
        )

    key_factors = [
        {"factor": "Recovery Probability", "value": f"{prob_pct:.1f}%", "impact": "High" if prob_pct >= 70 else "Medium"},
        {"factor": "Transaction Amount", "value": f"₹{amount:,.2f}", "impact": "High" if amount >= 10000 else "Standard"},
        {"factor": "Failure Reason", "value": reason.replace("_", " ").title(), "impact": "Permanent" if reason in PERMANENT_FAILURES else "Transient"},
        {"factor": "Opportunity Score", "value": f"{selected_eval['opportunity_score']:.1f} / 100", "impact": selected_eval['risk_level']},
        {"factor": "Safety Rule Compliance", "value": "ALLOWED" if is_allowed else "BLOCKED", "impact": "Authoritative"}
    ]

    return narrative, key_factors


# ==============================================================================
# 6. Scenario Comparison (Scenario A vs Scenario B)
# ==============================================================================

def compare_scenarios(scenario_a: Dict[str, Any], scenario_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two distinct simulation scenarios (Scenario A vs Scenario B).
    Computes differences in recovery probability, expected revenue, opportunity score,
    and produces a winner recommendation verdict.
    """
    res_a = run_recovery_simulation(scenario_a, scenario_a.get("strategy", "AUTOMATIC_RETRY"))
    res_b = run_recovery_simulation(scenario_b, scenario_b.get("strategy", "AUTOMATIC_RETRY"))

    prob_diff = round(res_a["recovery_probability"] - res_b["recovery_probability"], 4)
    prob_pct_diff = round(res_a["recovery_percentage"] - res_b["recovery_percentage"], 2)
    rev_diff = round(res_a["expected_recovery"] - res_b["expected_recovery"], 2)
    score_diff = round(res_a["opportunity_score"] - res_b["opportunity_score"], 1)

    if res_a["expected_recovery"] > res_b["expected_recovery"]:
        winner = "Scenario A"
        verdict = f"Scenario A outperforms Scenario B by +₹{rev_diff:,.2f} in expected recoverable revenue ({prob_pct_diff:+.1f}% probability)."
    elif res_b["expected_recovery"] > res_a["expected_recovery"]:
        winner = "Scenario B"
        verdict = f"Scenario B outperforms Scenario A by +₹{-rev_diff:,.2f} in expected recoverable revenue ({-prob_pct_diff:+.1f}% probability)."
    else:
        winner = "Tie"
        verdict = "Both scenarios produce equal expected recovery outcomes."

    return {
        "scenario_a": res_a,
        "scenario_b": res_b,
        "winner": winner,
        "verdict": verdict,
        "probability_diff": prob_diff,
        "probability_percentage_diff": prob_pct_diff,
        "expected_recovery_diff": rev_diff,
        "opportunity_score_diff": score_diff
    }


# ==============================================================================
# 7. Sensitivity Analysis & Failure Reason Matrix
# ==============================================================================

def generate_sensitivity_analysis(
    payment_data: Dict[str, Any],
    amounts: Optional[List[float]] = None
) -> List[Dict[str, Any]]:
    """
    Evaluate expected recovery across varying transaction amounts:
    Default: [₹1,000, ₹5,000, ₹10,000, ₹25,000, ₹50,000]
    """
    if amounts is None:
        amounts = [1000.0, 5000.0, 10000.0, 25000.0, 50000.0]

    results = []
    for amt in amounts:
        modified_payment = dict(payment_data)
        modified_payment["amount"] = float(amt)
        prob = predict_raw_probability(modified_payment)
        prob = round(prob, 4)
        exp_rev = round(amt * prob, 2)
        results.append({
            "amount": float(amt),
            "formatted_amount": f"₹{amt:,.2f}",
            "recovery_probability": round(prob, 4),
            "recovery_percentage": round(prob * 100.0, 2),
            "expected_recovery": exp_rev,
            "revenue_at_risk": float(amt)
        })

    return results


def generate_failure_reason_matrix(payment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Cross-compare how the AI decision, probability, expected recovery, and risk
    change across all failure reasons for the same customer profile.
    """
    results = []
    amount = float(payment_data.get("amount", 5000.0))

    for reason in VALID_FAILURE_REASONS:
        modified_payment = dict(payment_data)
        modified_payment["failure_reason"] = reason
        sim_res = run_recovery_simulation(modified_payment, selected_strategy="AUTOMATIC_RETRY")
        results.append({
            "failure_reason": reason,
            "formatted_reason": reason.replace("_", " ").title(),
            "is_permanent": reason in PERMANENT_FAILURES,
            "recovery_probability": sim_res["recovery_probability"],
            "recovery_percentage": sim_res["recovery_percentage"],
            "expected_recovery": sim_res["expected_recovery"],
            "recommended_action": sim_res["recommended_action"],
            "risk_level": sim_res["risk_level"],
            "best_strategy": sim_res["best_strategy_display"]
        })

    return results
