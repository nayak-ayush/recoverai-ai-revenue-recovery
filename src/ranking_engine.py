"""
RecoverAI Intelligent Revenue Opportunity Ranking Engine
Calculates transparent, explainable priority ranking scores for failed payments.
Combines recovery probability, expected revenue, action feasibility, customer history,
and strictly enforces safety rule overrides.
"""

from typing import Dict, Any, List, Optional
import math


def classify_priority_level(score: float) -> str:
    """
    Classify a 0-100 revenue opportunity score into priority categories:
    90.0 - 100.0 -> CRITICAL
    75.0 - 89.9  -> HIGH
    50.0 - 74.9  -> MEDIUM
    25.0 - 49.9  -> LOW
    0.0  - 24.9  -> VERY LOW
    """
    if score >= 90.0:
        return "CRITICAL"
    elif score >= 75.0:
        return "HIGH"
    elif score >= 50.0:
        return "MEDIUM"
    elif score >= 25.0:
        return "LOW"
    else:
        return "VERY LOW"


def calculate_opportunity_score(
    payment_amount: float,
    recovery_probability: float,
    expected_revenue: float,
    recommended_action: str,
    failure_reason: str,
    customer_info: Optional[Dict[str, Any]] = None,
    retry_count: int = 0
) -> Dict[str, Any]:
    """
    Compute transparent Revenue Opportunity Score (0-100) combining:
    1. Recovery Probability Score (40%)
    2. Revenue Value Score (35%)
    3. Recovery Action Score (15%)
    4. Customer/Payment Priority Score (10%)

    Returns the composite score, sub-scores, priority level, and explainability breakdown.
    """
    amount = max(0.0, float(payment_amount))
    prob = max(0.0, min(1.0, float(recovery_probability)))
    exp_rev = max(0.0, float(expected_revenue))
    action = str(recommended_action).upper()
    reason = str(failure_reason).lower()

    # 1. Recovery Probability Score (40% weight) -> 0 to 100
    prob_score = prob * 100.0

    # 2. Revenue Value Score (35% weight) -> 0 to 100
    # Uses calibrated linear scaling with target baseline ₹15,000 for high fintech opportunities, capped at 100
    rev_score = min(100.0, (exp_rev / 15000.0) * 100.0)

    # 3. Recovery Action Feasibility Score (15% weight) -> 0 to 100
    action_weights = {
        "RETRY_PAYMENT": 100.0,             # Instant automated recovery with lowest friction
        "SCHEDULE_RETRY": 80.0,             # Automated delayed recovery
        "SEND_PAYMENT_REMINDER": 55.0,      # Semi-automated customer nudge
        "CUSTOMER_ACTION_REQUIRED": 30.0,   # Requires user intervention (bank/card issue)
        "STOP_AUTOMATIC_RECOVERY": 10.0     # Low probability / high friction
    }
    action_score = action_weights.get(action, 50.0)

    # 4. Customer / Payment Priority Score (10% weight) -> 0 to 100
    cust = customer_info or {}
    previous_payments = cust.get("previous_payments", 5)
    previous_failures = cust.get("previous_failures", 1)
    subscription = cust.get("subscription", 0)

    cust_score = 70.0  # Base standard customer score
    if subscription == 1:
        cust_score += 15.0
    if previous_payments >= 10:
        cust_score += 15.0
    elif previous_payments >= 5:
        cust_score += 10.0

    if previous_failures >= 4:
        cust_score -= 15.0

    if retry_count == 0:
        cust_score += 10.0  # Fresh opportunity
    elif retry_count >= 2:
        cust_score -= 15.0  # Diminishing returns on repeated failures

    cust_score = max(0.0, min(100.0, cust_score))

    # Composite Weighted Formula
    raw_composite = (
        (0.40 * prob_score) +
        (0.35 * rev_score) +
        (0.15 * action_score) +
        (0.10 * cust_score)
    )

    final_score = round(max(0.0, min(100.0, raw_composite)), 1)
    priority_level = classify_priority_level(final_score)

    # Generate transparent explanation
    explanation = generate_opportunity_explanation(
        payment_amount=amount,
        recovery_probability=prob,
        expected_revenue=exp_rev,
        revenue_opportunity_score=final_score,
        priority_level=priority_level,
        recommended_action=action,
        failure_reason=reason
    )

    return {
        "revenue_opportunity_score": final_score,
        "priority_level": priority_level,
        "explanation": explanation,
        "sub_scores": {
            "probability_score": round(prob_score, 1),
            "revenue_value_score": round(rev_score, 1),
            "action_score": round(action_score, 1),
            "customer_priority_score": round(cust_score, 1)
        }
    }


def generate_opportunity_explanation(
    payment_amount: float,
    recovery_probability: float,
    expected_revenue: float,
    revenue_opportunity_score: float,
    priority_level: str,
    recommended_action: str,
    failure_reason: str
) -> str:
    """
    Generate deterministic, explainable rationale for why a payment received its priority rank.
    Strictly explains safety rule overrides for hard failures.
    """
    prob_pct = recovery_probability * 100.0
    clean_reason = failure_reason.replace("_", " ").title()
    permanent_failures = ["bank_decline", "authentication_failed", "expired_card"]

    if recommended_action == "CUSTOMER_ACTION_REQUIRED" or failure_reason in permanent_failures:
        return (
            f"Requires customer intervention for {clean_reason} failure. "
            f"Safety rules strictly prohibit automated retries regardless of payment amount (₹{payment_amount:,.2f}) "
            f"to protect merchant gateway health and prevent dispute penalties."
        )

    if priority_level == "CRITICAL":
        return (
            f"High-value payment (₹{payment_amount:,.2f}) with high recovery probability ({prob_pct:.1f}%) "
            f"and strong expected recoverable revenue (₹{expected_revenue:,.2f}). Highest priority for automated recovery."
        )
    elif priority_level == "HIGH":
        return (
            f"High priority recovery opportunity with favorable recovery probability ({prob_pct:.1f}%) "
            f"and substantial expected recovery of ₹{expected_revenue:,.2f}."
        )
    elif priority_level == "MEDIUM":
        if recovery_probability >= 0.60:
            return (
                f"Medium priority: good recovery probability ({prob_pct:.1f}%) with ₹{expected_revenue:,.2f} expected value, "
                f"queued for scheduled recovery retry."
            )
        else:
            return (
                f"Medium priority: recovery probability is moderate ({prob_pct:.1f}%) despite payment value of ₹{payment_amount:,.2f}. "
                f"Recommended recovery strategy is customer payment reminder."
            )
    elif priority_level == "LOW":
        return (
            f"Low priority because expected recovery value (₹{expected_revenue:,.2f}) is modest "
            f"and recovery probability is limited ({prob_pct:.1f}%)."
        )
    else:
        return (
            f"Very low priority: minimal expected recovery (₹{expected_revenue:,.2f}) and low model recovery confidence ({prob_pct:.1f}%). "
            f"Automatic recovery is halted."
        )


def rank_opportunities(
    opportunities: List[Dict[str, Any]],
    sort_by: str = "revenue_opportunity_score",
    sort_order: str = "desc"
) -> List[Dict[str, Any]]:
    """
    Sort list of opportunities and assign 1-indexed priority_rank.
    """
    if not opportunities:
        return []

    reverse = (sort_order.lower() == "desc")

    def sort_key(item: Dict[str, Any]):
        val = item.get(sort_by, 0)
        if val is None:
            val = 0
        return val

    # Primary sort by requested field, secondary sort by revenue_opportunity_score DESC
    sorted_items = sorted(
        opportunities,
        key=lambda x: (x.get(sort_by, 0), x.get("revenue_opportunity_score", 0)),
        reverse=reverse
    )

    ranked = []
    for idx, item in enumerate(sorted_items, start=1):
        item_copy = dict(item)
        item_copy["priority_rank"] = idx
        ranked.append(item_copy)

    return ranked
