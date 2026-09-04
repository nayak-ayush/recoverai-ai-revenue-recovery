"""
AI Decision Explanation Engine for RecoverAI
Provides deterministic, business-ready reasoning for payment recovery decisions.
"""

def format_failure_reason(reason: str) -> str:
    if not isinstance(reason, str):
        return str(reason)
    return reason.replace("_", " ").title()

def format_action_label(action: str) -> str:
    action_map = {
        "RETRY_PAYMENT": "Retry Payment",
        "SCHEDULE_RETRY": "Schedule Retry",
        "SEND_PAYMENT_REMINDER": "Send Payment Reminder",
        "CUSTOMER_ACTION_REQUIRED": "Customer Action Required",
        "STOP_AUTOMATIC_RECOVERY": "Stop Automatic Recovery"
    }
    return action_map.get(action, str(action).replace("_", " ").title())

def generate_decision_explanation(decision: dict) -> dict:
    """
    Generate structured, transparent explanation for a payment recovery decision.
    Based on actual ML recovery probability, failure reason, safety rules, and expected value.
    """
    amount = float(decision.get("payment_amount", 0.0))
    probability = float(decision.get("recovery_probability", 0.0))
    prob_pct = probability * 100
    expected_revenue = float(decision.get("expected_revenue", amount * probability))
    risk_level = str(decision.get("risk_level", "MEDIUM")).upper()
    action = str(decision.get("recommended_action", "STOP_AUTOMATIC_RECOVERY")).upper()
    failure_reason = str(decision.get("failure_reason", "unknown"))
    
    permanent_failures = ["bank_decline", "authentication_failed", "expired_card"]
    is_permanent = failure_reason in permanent_failures
    clean_reason = format_failure_reason(failure_reason)
    clean_action = format_action_label(action)

    # 1. Summary Narrative
    if is_permanent:
        summary = (
            f"RecoverAI identified this transaction as a permanent/hard failure ({clean_reason}). "
            f"Even though the statistical model estimated a {prob_pct:.1f}% potential baseline probability, "
            f"the safety rule engine immediately intervened to classify this as HIGH RISK and require customer action "
            f"to prevent wasteful gateway retries and potential chargeback fees."
        )
        flow_active_step = "Safety Rules Evaluated (Hard Failure Interception)"
    elif action == "RETRY_PAYMENT":
        summary = (
            f"RecoverAI predicted a high recovery probability of {prob_pct:.1f}% for this {clean_reason} failure. "
            f"Because this failure type is transient and recoverable, the transaction is classified as LOW RISK, "
            f"and an immediate automatic retry is recommended to maximize recovered revenue."
        )
        flow_active_step = "Safety Rules & Thresholds Evaluated (≥80% High Confidence)"
    elif action == "SCHEDULE_RETRY":
        summary = (
            f"RecoverAI predicted a moderate-high recovery probability of {prob_pct:.1f}%. "
            f"For {clean_reason}, immediate retries have diminishing returns, so a delayed/scheduled retry "
            f"is recommended during the customer's next optimal payment window."
        )
        flow_active_step = "Safety Rules & Thresholds Evaluated (60%-79% Moderate Confidence)"
    elif action == "SEND_PAYMENT_REMINDER":
        summary = (
            f"RecoverAI estimated a {prob_pct:.1f}% recovery probability. Direct automated retries carry medium risk, "
            f"so sending an interactive payment reminder (via WhatsApp / SMS / Email) is the optimal recovery vector."
        )
        flow_active_step = "Safety Rules & Thresholds Evaluated (40%-59% Reminder Tier)"
    else:
        summary = (
            f"RecoverAI determined a low recovery probability of {prob_pct:.1f}%. "
            f"Automatic recovery is halted to prevent negative customer friction and redundant processing fees."
        )
        flow_active_step = "Safety Rules & Thresholds Evaluated (<40% Low Confidence)"

    # 2. Key Decision Factors (3 to 5 dynamic items)
    factors = []
    
    # Factor 1: Model Probability
    if prob_pct >= 80:
        factors.append(f"High ML Model Confidence: {prob_pct:.1f}% recovery probability predicted by Random Forest pipeline.")
    elif prob_pct >= 60:
        factors.append(f"Moderate ML Model Confidence: {prob_pct:.1f}% recovery probability based on customer payment history.")
    elif prob_pct >= 40:
        factors.append(f"Sub-optimal Recovery Probability: {prob_pct:.1f}% estimated probability.")
    else:
        factors.append(f"Low Recovery Probability: Only {prob_pct:.1f}% predicted recovery likelihood.")

    # Factor 2: Failure Modality & Safety Rules
    if is_permanent:
        factors.append(f"Critical Safety Rule Triggered: '{clean_reason}' is classified as a non-retryable hard failure.")
        factors.append("Chargeback & Penalty Protection: Automated retries disabled to protect merchant gateway health.")
    else:
        factors.append(f"Transient Failure Type: '{clean_reason}' is eligible for automated recovery workflows.")
        factors.append(f"Permitted Action: Gateway policy allows automated retry strategy for this failure mode.")

    # Factor 3: Economic / Expected Revenue Factor
    factors.append(
        f"Recoverable Revenue Potential: ₹{expected_revenue:,.2f} expected value out of ₹{amount:,.2f} at stake."
    )

    # Factor 4: Risk Tier
    factors.append(f"Risk Classification: Assigned {risk_level} RISK tier based on failure category and probability thresholds.")

    # 3. Risk Explanation
    if risk_level == "LOW":
        risk_explanation = (
            "LOW RISK: The failure reason is transient (e.g., temporary network hiccup or system timeout), "
            "and model confidence is high (≥80%). Low likelihood of customer dispute."
        )
    elif risk_level == "MEDIUM":
        risk_explanation = (
            "MEDIUM RISK: Recovery is viable (40%–79%), but requires pacing or customer nudges "
            "rather than aggressive rapid retries."
        )
    else:
        risk_explanation = (
            "HIGH RISK: High probability of permanent decline or repeated failure. "
            "Automated programmatic retries are restricted to protect merchant reputation."
        )

    # 4. Action Explanation & Next Step
    if action == "RETRY_PAYMENT":
        action_explanation = "Immediate automatic retry executed via fallback payment routing."
        next_step = "Trigger automated smart retry through alternate bank switch or payment gateway route."
    elif action == "SCHEDULE_RETRY":
        action_explanation = "Delayed retry scheduled for next optimal banking window (e.g. 4–12 hours)."
        next_step = "Queue transaction in smart retry scheduler for off-peak retry execution."
    elif action == "SEND_PAYMENT_REMINDER":
        action_explanation = "Proactive digital reminder with 1-click payment link."
        next_step = "Dispatch instant payment link via WhatsApp and email to allow customer to complete checkout."
    elif action == "CUSTOMER_ACTION_REQUIRED":
        action_explanation = "User intervention required (e.g., update card details, contact bank, or approve 2FA)."
        next_step = "Prompt customer with clear action instructions to update their card or verify with their bank."
    else:
        action_explanation = "Automatic recovery halted; mark transaction as unrecoverable."
        next_step = "Log transaction as closed/unrecoverable; notify merchant analytics dashboard."

    # 5. Math calculation string
    calc_math = f"₹{amount:,.2f} × {prob_pct:.1f}% = ₹{expected_revenue:,.2f}"

    return {
        "summary": summary,
        "factors": factors,
        "risk_explanation": risk_explanation,
        "action_explanation": action_explanation,
        "expected_revenue_explanation": calc_math,
        "next_step": next_step,
        "flow_active_step": flow_active_step,
        "risk_level": risk_level,
        "recommended_action": action,
        "formatted_action": clean_action,
        "formatted_reason": clean_reason,
        "payment_amount": amount,
        "recovery_probability": probability,
        "recovery_percentage": prob_pct,
        "expected_revenue": expected_revenue
    }
