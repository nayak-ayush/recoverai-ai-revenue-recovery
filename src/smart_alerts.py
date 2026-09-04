"""
RecoverAI Smart Alert Engine
Automatically detects critical revenue-recovery situations from payment and decision data.
Provides priority classification, transparent alert scoring, deduplication, explainability,
and lifecycle management (OPEN -> ACKNOWLEDGED -> RESOLVED).
"""

import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Setup path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ==============================================================================
# 1. Central Smart Alert Configuration
# ==============================================================================

class SmartAlertConfig:
    """Configurable business thresholds for Smart Alerts."""
    HIGH_VALUE_THRESHOLD: float = 10000.0
    CRITICAL_VALUE_THRESHOLD: float = 20000.0
    SIGNIFICANT_LOSS_THRESHOLD: float = 7000.0
    
    LOW_RECOVERY_PROBABILITY_THRESHOLD: float = 0.40
    HIGH_RECOVERY_PROBABILITY_THRESHOLD: float = 0.75
    VERY_HIGH_RECOVERY_PROBABILITY_THRESHOLD: float = 0.80
    
    CRITICAL_OPPORTUNITY_SCORE: float = 90.0
    HIGH_OPPORTUNITY_SCORE: float = 75.0
    
    SPIKE_MIN_COUNT: int = 3
    SPIKE_MIN_AMOUNT: float = 10000.0
    LOOKBACK_HOURS: int = 24
    
    BASELINE_RECOVERY_RATE: float = 0.70
    PERFORMANCE_DROP_THRESHOLD: float = 0.25  # 25% drop

    # Outcome-based alert thresholds
    HIGH_VALUE_RECOVERY_CONFIRMED_THRESHOLD: float = 10000.0
    MODEL_MISMATCH_THRESHOLD: float = 0.30   # Prob gap > 30% triggers mismatch alert
    HIGH_RISK_REMAINING_THRESHOLD: float = 50000.0  # ₹50k+ still at risk


# ==============================================================================
# 2. Alert Scoring & Priority Logic
# ==============================================================================

def calculate_alert_priority(
    alert_type: str,
    amount: float,
    recovery_probability: float,
    opportunity_score: float,
    risk_level: str
) -> str:
    """
    Determine alert priority: CRITICAL, HIGH, MEDIUM, LOW.
    Opportunity score provides the baseline, overridden by critical business conditions.
    """
    # Business-critical overrides
    if alert_type == "CRITICAL_OPPORTUNITY" or opportunity_score >= SmartAlertConfig.CRITICAL_OPPORTUNITY_SCORE:
        return "CRITICAL"
    
    if alert_type == "REVENUE_SPIKE_RISK":
        return "CRITICAL"
    
    if alert_type == "HIGH_REVENUE_RISK" and amount >= SmartAlertConfig.HIGH_VALUE_THRESHOLD:
        return "CRITICAL"
    
    if alert_type == "CUSTOMER_ACTION_REQUIRED" and amount >= SmartAlertConfig.CRITICAL_VALUE_THRESHOLD:
        return "CRITICAL"

    # Outcome-based alerts
    if alert_type == "HIGH_VALUE_RECOVERY_CONFIRMED" and amount >= SmartAlertConfig.HIGH_VALUE_RECOVERY_CONFIRMED_THRESHOLD:
        return "HIGH"
    if alert_type == "RECOVERY_FAILED" and amount >= SmartAlertConfig.HIGH_VALUE_THRESHOLD:
        return "HIGH"
    if alert_type == "MODEL_PREDICTION_MISMATCH":
        return "HIGH"
    if alert_type == "HIGH_REVENUE_STILL_AT_RISK":
        return "CRITICAL"
    if alert_type == "RECOVERY_SUCCESS":
        return "LOW"
    if alert_type == "RECOVERY_FAILED":
        return "MEDIUM"
    
    if opportunity_score >= SmartAlertConfig.HIGH_OPPORTUNITY_SCORE or amount >= SmartAlertConfig.HIGH_VALUE_THRESHOLD:
        return "HIGH"
    
    if alert_type in ["HIGH_VALUE_RECOVERY", "CUSTOMER_ACTION_REQUIRED", "RECOVERY_PERFORMANCE_DROP"]:
        return "HIGH"
    
    if opportunity_score >= 50.0:
        return "MEDIUM"
    elif alert_type in ["RETRY_RECOMMENDED", "LOW_RECOVERY_PROBABILITY"]:
        return "MEDIUM"
    
    return "LOW"


def calculate_alert_score(
    amount: float,
    recovery_probability: float,
    opportunity_score: float,
    risk_level: str,
    alert_type: str
) -> float:
    """
    Transparent 0–100 Alert Severity Score.
    Higher score indicates higher operational urgency.
    """
    # 1. Financial Exposure Score (0-40 pts)
    amt_score = min(40.0, (amount / 25000.0) * 40.0)
    
    # 2. Opportunity / Loss Urgency Score (0-30 pts)
    opp_score = (opportunity_score / 100.0) * 30.0
    
    # 3. Risk Level Component (0-20 pts)
    risk_points = {"HIGH": 20.0, "MEDIUM": 10.0, "LOW": 5.0}.get(risk_level.upper(), 10.0)
    
    # 4. Type Urgency Boost (0-10 pts)
    type_boosts = {
        "CRITICAL_OPPORTUNITY": 10.0,
        "HIGH_REVENUE_RISK": 10.0,
        "REVENUE_SPIKE_RISK": 10.0,
        "HIGH_VALUE_RECOVERY": 8.0,
        "CUSTOMER_ACTION_REQUIRED": 7.0,
        "RECOVERY_PERFORMANCE_DROP": 8.0,
        "RETRY_RECOMMENDED": 6.0,
        "LOW_RECOVERY_PROBABILITY": 5.0,
        # Outcome-based alert boosts
        "RECOVERY_SUCCESS": 3.0,
        "HIGH_VALUE_RECOVERY_CONFIRMED": 6.0,
        "RECOVERY_FAILED": 7.0,
        "RECOVERY_PERFORMANCE_DROP_ACTUAL": 9.0,
        "MODEL_PREDICTION_MISMATCH": 8.0,
        "HIGH_REVENUE_STILL_AT_RISK": 10.0
    }
    boost = type_boosts.get(alert_type, 5.0)
    
    total = amt_score + opp_score + risk_points + boost
    return round(max(0.0, min(100.0, total)), 1)


# ==============================================================================
# 3. Explainability Generators
# ==============================================================================

def generate_alert_explanation(
    alert_type: str,
    amount: float,
    recovery_probability: float,
    risk_level: str,
    opportunity_score: float,
    recommended_action: str,
    expected_recovery: float
) -> tuple[str, str, str, str]:
    """
    Returns (title, message, why_explanation, recommended_step).
    """
    prob_pct = recovery_probability * 100.0
    
    if alert_type == "HIGH_REVENUE_RISK":
        title = "High-Value Revenue at Risk"
        message = f"₹{amount:,.2f} transaction has HIGH risk classification with ₹{amount - expected_recovery:,.2f} potential loss."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Payment Amount: ₹{amount:,.2f}\n"
            f"• Recovery Probability: {prob_pct:.1f}%\n"
            f"• Risk Classification: {risk_level}\n"
            f"• Expected Recoverable: ₹{expected_recovery:,.2f}\n"
            f"TRIGGER: Significant transaction value exposed to severe failure risk."
        )
        step = "Review gateway decline logs and prepare manual account escalation or alternate payment collection."

    elif alert_type == "CRITICAL_OPPORTUNITY":
        title = "Critical Recovery Opportunity"
        message = f"Top-priority recoverable revenue: ₹{expected_recovery:,.2f} expected from ₹{amount:,.2f} payment (Score: {opportunity_score:.1f})."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Opportunity Score: {opportunity_score:.1f} (≥ 90.0 CRITICAL threshold)\n"
            f"• Recovery Probability: {prob_pct:.1f}%\n"
            f"• Expected Recovery: ₹{expected_recovery:,.2f}\n"
            f"TRIGGER: Elite combination of high transaction value and strong AI recovery confidence."
        )
        step = "Execute immediate smart retry routing through primary backup gateway switch."

    elif alert_type == "HIGH_VALUE_RECOVERY":
        title = "High-Value Recoverable Payment"
        message = f"High-ticket payment of ₹{amount:,.2f} with strong recovery likelihood ({prob_pct:.1f}%)."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Payment Amount: ₹{amount:,.2f} (≥ ₹{SmartAlertConfig.HIGH_VALUE_THRESHOLD:,.2f})\n"
            f"• Recovery Probability: {prob_pct:.1f}%\n"
            f"TRIGGER: High-value transaction exceeding configured threshold with favorable recovery odds."
        )
        step = "Prioritize automated recovery queue and monitor settlement confirmation."

    elif alert_type == "LOW_RECOVERY_PROBABILITY":
        title = "Low Recovery Probability Detected"
        message = f"₹{amount:,.2f} payment has very low recovery likelihood ({prob_pct:.1f}%)."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Recovery Probability: {prob_pct:.1f}% (≤ {SmartAlertConfig.LOW_RECOVERY_PROBABILITY_THRESHOLD * 100:.0f}%)\n"
            f"• Payment Amount: ₹{amount:,.2f}\n"
            f"TRIGGER: High probability of permanent failure. Automated retries will likely fail."
        )
        step = "Halt automated retry loops to avoid repeated gateway fees and customer friction."

    elif alert_type == "CUSTOMER_ACTION_REQUIRED":
        title = "Customer Action Required (Hard Failure)"
        message = f"₹{amount:,.2f} failed due to permanent/hard decline. Safety rules prohibit automated retries."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Action: CUSTOMER_ACTION_REQUIRED\n"
            f"• Payment Amount: ₹{amount:,.2f}\n"
            f"• Risk Level: HIGH\n"
            f"TRIGGER: Bank decline, expired card, or 2FA authentication failure intercepted by safety rules."
        )
        step = "Dispatch instant payment update link via WhatsApp/SMS for customer to update card or verify with bank."

    elif alert_type == "RETRY_RECOMMENDED":
        title = "Automated Retry Recommended"
        message = f"Model predicts high success probability ({prob_pct:.1f}%) for ₹{amount:,.2f} transient failure."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Recovery Probability: {prob_pct:.1f}% (≥ {SmartAlertConfig.VERY_HIGH_RECOVERY_PROBABILITY_THRESHOLD * 100:.0f}%)\n"
            f"• Recommended Action: RETRY_PAYMENT\n"
            f"TRIGGER: Transient network/system failure eligible for instant automated recovery."
        )
        step = "Trigger immediate automated retry via alternate banking switch."

    elif alert_type == "REVENUE_SPIKE_RISK":
        title = "Revenue Failure Spike Detected"
        message = f"Multiple high-value failed payments (≥ ₹{SmartAlertConfig.SPIKE_MIN_AMOUNT:,.0f}) detected in short succession."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Spike Condition: ≥ {SmartAlertConfig.SPIKE_MIN_COUNT} high-value failures in {SmartAlertConfig.LOOKBACK_HOURS}h window\n"
            f"TRIGGER: Anomalous surge in high-ticket transaction failures."
        )
        step = "Check payment gateway uptime, webhook delivery, and issuer bank health status."

    elif alert_type == "RECOVERY_PERFORMANCE_DROP":
        title = "Recovery Success Rate Drop"
        message = f"Recent batch recovery confidence dropped significantly below historical baseline."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Baseline Rate: {SmartAlertConfig.BASELINE_RECOVERY_RATE * 100:.0f}%\n"
            f"• Drop Threshold: {SmartAlertConfig.PERFORMANCE_DROP_THRESHOLD * 100:.0f}%\n"
            f"TRIGGER: Significant degradation in payment recovery yield."
        )
        step = "Inspect routing rules, card network latencies, and customer authentication pipelines."

    elif alert_type == "RECOVERY_SUCCESS":
        title = "Payment Recovery Successful"
        message = f"₹{amount:,.2f} successfully recovered via automated recovery workflow."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Recovered Amount: ₹{amount:,.2f}\n"
            f"• Original Prediction: {prob_pct:.1f}%\n"
            f"TRIGGER: Recovery outcome confirmed as RECOVERED."
        )
        step = "Update revenue dashboard. Consider this payment resolved."

    elif alert_type == "HIGH_VALUE_RECOVERY_CONFIRMED":
        title = "High-Value Recovery Confirmed"
        message = f"₹{amount:,.2f} high-value payment successfully recovered."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Recovered Amount: ₹{amount:,.2f} (≥ ₹{SmartAlertConfig.HIGH_VALUE_RECOVERY_CONFIRMED_THRESHOLD:,.0f})\n"
            f"• Recovery Probability Was: {prob_pct:.1f}%\n"
            f"TRIGGER: Significant high-value recovery confirmed."
        )
        step = "Log recovery success. Review for recurring failure pattern prevention."

    elif alert_type == "RECOVERY_FAILED":
        title = "Recovery Attempt Failed"
        message = f"₹{amount:,.2f} recovery attempt was unsuccessful. Revenue remains at risk."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Payment Amount: ₹{amount:,.2f}\n"
            f"• Predicted Recovery: {prob_pct:.1f}%\n"
            f"TRIGGER: Recovery outcome confirmed as NOT_RECOVERED / RETRY_FAILED."
        )
        step = "Review failure reason. Consider escalating to manual recovery or customer notification."

    elif alert_type == "MODEL_PREDICTION_MISMATCH":
        title = "AI Prediction Mismatch Detected"
        message = f"Significant gap between AI recovery prediction ({prob_pct:.1f}%) and actual outcome."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Predicted Probability: {prob_pct:.1f}%\n"
            f"• Gap Threshold: {SmartAlertConfig.MODEL_MISMATCH_THRESHOLD * 100:.0f}%\n"
            f"TRIGGER: Model prediction significantly diverged from actual recovery outcome."
        )
        step = "Review model performance. Collect feedback data for future model calibration."

    elif alert_type == "HIGH_REVENUE_STILL_AT_RISK":
        title = "High Revenue Still at Risk"
        message = f"₹{amount:,.2f} in failed payments remain unrecovered."
        why = (
            f"WHY THIS ALERT?\n"
            f"• Revenue Still at Risk: ₹{amount:,.2f}\n"
            f"• Threshold: ₹{SmartAlertConfig.HIGH_RISK_REMAINING_THRESHOLD:,.0f}\n"
            f"TRIGGER: Aggregate unrecovered revenue exceeds critical threshold."
        )
        step = "Escalate high-value unrecovered payments to senior recovery team."

    else:
        title = f"Alert: {alert_type.replace('_', ' ').title()}"
        message = f"Payment ₹{amount:,.2f} requires operational attention."
        why = f"Alert triggered for payment {amount} with status {recommended_action}."
        step = "Inspect transaction details in Payment Operations queue."

    return title, message, why, step


# ==============================================================================
# 4. Decision Evaluation & Alert Generation
# ==============================================================================

def evaluate_decision_for_alerts(decision: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluate a single recovery decision dictionary and return candidate alerts.
    """
    alerts = []
    
    amount = float(decision.get("payment_amount", 0.0))
    prob = float(decision.get("recovery_probability", 0.0))
    exp_rev = float(decision.get("expected_revenue", amount * prob))
    risk = str(decision.get("risk_level", "MEDIUM")).upper()
    action = str(decision.get("recommended_action", "STOP_AUTOMATIC_RECOVERY")).upper()
    opp_score = float(decision.get("revenue_opportunity_score", 0.0))
    pid = decision.get("payment_id") or f"PAY{decision.get('id', 1):05d}"
    cid = decision.get("customer_id") or "CUST0001"
    
    # 1. CRITICAL_OPPORTUNITY (Opportunity score >= 90)
    if opp_score >= SmartAlertConfig.CRITICAL_OPPORTUNITY_SCORE:
        alerts.append({
            "alert_type": "CRITICAL_OPPORTUNITY",
            "payment_id": pid,
            "customer_id": cid,
            "amount": amount,
            "recovery_probability": prob,
            "risk_level": risk,
            "opportunity_score": opp_score,
            "recommended_action": action,
            "expected_recovery": exp_rev
        })
        
    # 2. HIGH_REVENUE_RISK (Risk = HIGH AND (amount >= 10k OR loss >= 7k))
    expected_loss = amount - exp_rev
    if risk == "HIGH" and (amount >= SmartAlertConfig.HIGH_VALUE_THRESHOLD or expected_loss >= SmartAlertConfig.SIGNIFICANT_LOSS_THRESHOLD):
        alerts.append({
            "alert_type": "HIGH_REVENUE_RISK",
            "payment_id": pid,
            "customer_id": cid,
            "amount": amount,
            "recovery_probability": prob,
            "risk_level": risk,
            "opportunity_score": opp_score,
            "recommended_action": action,
            "expected_recovery": exp_rev
        })
        
    # 3. HIGH_VALUE_RECOVERY (Amount >= 10k AND prob >= 0.70)
    if amount >= SmartAlertConfig.HIGH_VALUE_THRESHOLD and prob >= SmartAlertConfig.HIGH_RECOVERY_PROBABILITY_THRESHOLD and action == "RETRY_PAYMENT":
        alerts.append({
            "alert_type": "HIGH_VALUE_RECOVERY",
            "payment_id": pid,
            "customer_id": cid,
            "amount": amount,
            "recovery_probability": prob,
            "risk_level": risk,
            "opportunity_score": opp_score,
            "recommended_action": action,
            "expected_recovery": exp_rev
        })
        
    # 4. CUSTOMER_ACTION_REQUIRED (Hard failures)
    if action == "CUSTOMER_ACTION_REQUIRED":
        alerts.append({
            "alert_type": "CUSTOMER_ACTION_REQUIRED",
            "payment_id": pid,
            "customer_id": cid,
            "amount": amount,
            "recovery_probability": prob,
            "risk_level": risk,
            "opportunity_score": opp_score,
            "recommended_action": action,
            "expected_recovery": exp_rev
        })
        
    # 5. RETRY_RECOMMENDED (Prob >= 80% AND RETRY_PAYMENT)
    if prob >= SmartAlertConfig.VERY_HIGH_RECOVERY_PROBABILITY_THRESHOLD and action == "RETRY_PAYMENT" and opp_score < SmartAlertConfig.CRITICAL_OPPORTUNITY_SCORE and amount < SmartAlertConfig.HIGH_VALUE_THRESHOLD:
        alerts.append({
            "alert_type": "RETRY_RECOMMENDED",
            "payment_id": pid,
            "customer_id": cid,
            "amount": amount,
            "recovery_probability": prob,
            "risk_level": risk,
            "opportunity_score": opp_score,
            "recommended_action": action,
            "expected_recovery": exp_rev
        })
        
    # 6. LOW_RECOVERY_PROBABILITY (Prob <= 40% AND amount >= 3000)
    if prob <= SmartAlertConfig.LOW_RECOVERY_PROBABILITY_THRESHOLD and amount >= 3000.0 and action != "CUSTOMER_ACTION_REQUIRED":
        alerts.append({
            "alert_type": "LOW_RECOVERY_PROBABILITY",
            "payment_id": pid,
            "customer_id": cid,
            "amount": amount,
            "recovery_probability": prob,
            "risk_level": risk,
            "opportunity_score": opp_score,
            "recommended_action": action,
            "expected_recovery": exp_rev
        })

    return alerts


def evaluate_system_alerts(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluate macro / system-level alerts across decisions (e.g. spikes, drops).
    """
    alerts = []
    if not decisions or len(decisions) < 3:
        return alerts

    # Check for REVENUE_SPIKE_RISK: >= 3 payments >= 10,000
    high_value_failures = [d for d in decisions if float(d.get("payment_amount", 0.0)) >= SmartAlertConfig.SPIKE_MIN_AMOUNT]
    if len(high_value_failures) >= SmartAlertConfig.SPIKE_MIN_COUNT:
        total_spike_amt = sum(float(d.get("payment_amount", 0.0)) for d in high_value_failures)
        today_str = datetime.now().strftime("%Y-%m-%d")
        alerts.append({
            "alert_type": "REVENUE_SPIKE_RISK",
            "payment_id": None,
            "customer_id": None,
            "amount": total_spike_amt,
            "recovery_probability": 0.5,
            "risk_level": "HIGH",
            "opportunity_score": 85.0,
            "recommended_action": "SYSTEM_INVESTIGATION",
            "expected_recovery": total_spike_amt * 0.5,
            "time_window_key": today_str
        })

    # Check for RECOVERY_PERFORMANCE_DROP: average prob of last 5 decisions < 0.45
    recent_probs = [float(d.get("recovery_probability", 0.0)) for d in decisions[:10]]
    if recent_probs and len(recent_probs) >= 5:
        avg_prob = sum(recent_probs) / len(recent_probs)
        if avg_prob <= (SmartAlertConfig.BASELINE_RECOVERY_RATE - SmartAlertConfig.PERFORMANCE_DROP_THRESHOLD):
            today_str = datetime.now().strftime("%Y-%m-%d")
            total_amt = sum(float(d.get("payment_amount", 0.0)) for d in decisions[:10])
            alerts.append({
                "alert_type": "RECOVERY_PERFORMANCE_DROP",
                "payment_id": None,
                "customer_id": None,
                "amount": total_amt,
                "recovery_probability": avg_prob,
                "risk_level": "HIGH",
                "opportunity_score": 75.0,
                "recommended_action": "OPTIMIZE_RECOVERY_ROUTING",
                "expected_recovery": total_amt * avg_prob,
                "time_window_key": today_str
            })

    return alerts


def build_alert_record(raw_alert: Dict[str, Any], alert_num: int = 1) -> Dict[str, Any]:
    """
    Format and compute full metadata for a Smart Alert record ready for database insertion.
    """
    alert_type = raw_alert["alert_type"]
    amount = float(raw_alert.get("amount", 0.0))
    prob = float(raw_alert.get("recovery_probability", 0.0))
    opp_score = float(raw_alert.get("opportunity_score", 0.0))
    risk = str(raw_alert.get("risk_level", "MEDIUM")).upper()
    action = str(raw_alert.get("recommended_action", "STOP_AUTOMATIC_RECOVERY"))
    exp_rev = float(raw_alert.get("expected_recovery", amount * prob))
    pid = raw_alert.get("payment_id")
    cid = raw_alert.get("customer_id")
    
    # Priority
    priority = calculate_alert_priority(
        alert_type=alert_type,
        amount=amount,
        recovery_probability=prob,
        opportunity_score=opp_score,
        risk_level=risk
    )
    
    # Text Explanations
    title, message, why, step = generate_alert_explanation(
        alert_type=alert_type,
        amount=amount,
        recovery_probability=prob,
        risk_level=risk,
        opportunity_score=opp_score,
        recommended_action=action,
        expected_recovery=exp_rev
    )
    
    # Deduplication key
    if pid:
        dedup_key = f"{alert_type}:{pid}"
    else:
        window = raw_alert.get("time_window_key", datetime.now().strftime("%Y-%m-%d"))
        dedup_key = f"{alert_type}:{window}"
        
    alert_id = f"ALT-{uuid.uuid4().hex[:6].upper()}"
    
    return {
        "alert_id": alert_id,
        "alert_type": alert_type,
        "priority": priority,
        "title": title,
        "message": message,
        "payment_id": pid,
        "customer_id": cid,
        "amount": amount,
        "recovery_probability": round(prob, 4),
        "risk_level": risk,
        "opportunity_score": round(opp_score, 1),
        "recommended_action": action,
        "expected_recovery": round(exp_rev, 2),
        "status": "OPEN",
        "dedup_key": dedup_key,
        "why_explanation": why,
        "recommended_step": step,
        "created_at": datetime.now().isoformat()
    }


# ==============================================================================
# 5. Recovery Outcome Alert Evaluation
# ==============================================================================

def evaluate_outcome_for_alerts(outcome: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Evaluate a completed recovery outcome dict and return candidate alerts.
    Only called after a recovery outcome is finalized (SUCCESS or FAILED).
    Prevents duplicate alerts via dedup_key.
    """
    alerts = []

    pid = outcome.get("payment_id") or "UNKNOWN"
    cid = outcome.get("customer_id")
    amount = float(outcome.get("payment_amount") or 0.0)
    recovered = float(outcome.get("recovered_amount") or 0.0)
    prob = float(outcome.get("recovery_probability") or 0.0)
    status = str(outcome.get("status") or "").upper()
    outcome_val = str(outcome.get("outcome") or "").upper()
    expected_recovery = float(outcome.get("expected_recovery") or 0.0)

    # 1. RECOVERY_SUCCESS — any successful recovery
    if status == "SUCCESS" and outcome_val == "RECOVERED":
        alerts.append({
            "alert_type": "RECOVERY_SUCCESS",
            "payment_id": pid,
            "customer_id": cid,
            "amount": recovered,
            "recovery_probability": prob,
            "risk_level": "LOW",
            "opportunity_score": 40.0,
            "recommended_action": "NONE",
            "expected_recovery": expected_recovery
        })

        # 2. HIGH_VALUE_RECOVERY_CONFIRMED — high-value successful recovery
        if recovered >= SmartAlertConfig.HIGH_VALUE_RECOVERY_CONFIRMED_THRESHOLD:
            alerts.append({
                "alert_type": "HIGH_VALUE_RECOVERY_CONFIRMED",
                "payment_id": pid,
                "customer_id": cid,
                "amount": recovered,
                "recovery_probability": prob,
                "risk_level": "LOW",
                "opportunity_score": 70.0,
                "recommended_action": "NONE",
                "expected_recovery": expected_recovery
            })

    # 3. RECOVERY_FAILED — failed recovery
    if status == "FAILED":
        alerts.append({
            "alert_type": "RECOVERY_FAILED",
            "payment_id": pid,
            "customer_id": cid,
            "amount": amount,
            "recovery_probability": prob,
            "risk_level": "HIGH",
            "opportunity_score": 60.0,
            "recommended_action": "INVESTIGATE",
            "expected_recovery": expected_recovery
        })

    # 4. MODEL_PREDICTION_MISMATCH — large gap between prediction and outcome
    if prob > 0 and status in ("SUCCESS", "FAILED"):
        actual = 1.0 if outcome_val == "RECOVERED" else 0.0
        gap = abs(actual - prob)
        if gap >= SmartAlertConfig.MODEL_MISMATCH_THRESHOLD:
            alerts.append({
                "alert_type": "MODEL_PREDICTION_MISMATCH",
                "payment_id": pid,
                "customer_id": cid,
                "amount": amount,
                "recovery_probability": prob,
                "risk_level": "MEDIUM",
                "opportunity_score": 65.0,
                "recommended_action": "REVIEW_MODEL",
                "expected_recovery": expected_recovery
            })

    return alerts


def evaluate_system_outcome_alerts(outcomes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate system-level alerts from aggregate outcome data.
    Checks: HIGH_REVENUE_STILL_AT_RISK, RECOVERY_PERFORMANCE_DROP_ACTUAL.
    """
    alerts = []
    if not outcomes:
        return alerts

    # HIGH_REVENUE_STILL_AT_RISK — large amount of revenue not recovered
    failed = [o for o in outcomes if o.get("status") == "FAILED"]
    revenue_still_at_risk = sum(float(o.get("revenue_at_risk") or o.get("payment_amount") or 0) for o in failed)
    if revenue_still_at_risk >= SmartAlertConfig.HIGH_RISK_REMAINING_THRESHOLD:
        today_str = datetime.now().strftime("%Y-%m-%d")
        alerts.append({
            "alert_type": "HIGH_REVENUE_STILL_AT_RISK",
            "payment_id": None,
            "customer_id": None,
            "amount": revenue_still_at_risk,
            "recovery_probability": 0.0,
            "risk_level": "HIGH",
            "opportunity_score": 80.0,
            "recommended_action": "ESCALATE_RECOVERY",
            "expected_recovery": 0.0,
            "time_window_key": today_str
        })

    # RECOVERY_PERFORMANCE_DROP_ACTUAL — actual recovery rate significantly below threshold
    completed = [o for o in outcomes if o.get("status") in ("SUCCESS", "FAILED")]
    if len(completed) >= 5:
        successful_c = sum(1 for o in completed if o.get("status") == "SUCCESS")
        actual_rate = successful_c / len(completed)
        if actual_rate <= (SmartAlertConfig.BASELINE_RECOVERY_RATE - SmartAlertConfig.PERFORMANCE_DROP_THRESHOLD):
            today_str = datetime.now().strftime("%Y-%m-%d")
            total_at_risk = sum(float(o.get("revenue_at_risk") or 0) for o in completed)
            alerts.append({
                "alert_type": "RECOVERY_PERFORMANCE_DROP",
                "payment_id": None,
                "customer_id": None,
                "amount": total_at_risk,
                "recovery_probability": actual_rate,
                "risk_level": "HIGH",
                "opportunity_score": 75.0,
                "recommended_action": "OPTIMIZE_RECOVERY_ROUTING",
                "expected_recovery": total_at_risk * actual_rate,
                "time_window_key": today_str
            })

    return alerts
