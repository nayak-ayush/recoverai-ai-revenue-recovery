import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, validator
from src.recovery_agent import recovery_agent
from src.database import (
    create_database,
    save_decision,
    get_decisions,
    get_recovery_opportunities,
    get_alerts,
    get_alert_by_id,
    acknowledge_alert_db,
    resolve_alert_db,
    get_alerts_summary_metrics,
    sync_smart_alerts,
    save_simulation,
    get_simulations,
    get_simulation_by_id,
    # New recovery outcome functions
    record_recovery_attempt,
    create_recovery_outcome_record,
    save_recovery_outcome,
    advance_outcome_to_attempted,
    get_recovery_outcomes,
    get_recovery_outcome_by_id,
    update_recovery_outcome,
    get_recovery_metrics,
    get_recovery_performance_by_strategy,
    get_recovery_performance_by_failure_reason,
    get_customer_recovery_history,
    get_feedback_metrics,
    get_audit_log,
    VALID_OUTCOMES,
    VALID_STATUSES,
    STATUS_TRANSITIONS,
    save_alert
)
from src.explanation_engine import generate_decision_explanation
from src.recovery_simulator import (
    run_recovery_simulation,
    evaluate_all_strategies,
    compare_scenarios,
    generate_sensitivity_analysis,
    generate_failure_reason_matrix,
    VALID_FAILURE_REASONS,
    VALID_PAYMENT_METHODS,
    STRATEGY_NAMES
)


# ==========================================
# Create FastAPI application
# ==========================================

app = FastAPI(
    title="RecoverAI",
    description=(
        "AI-powered payment revenue recovery, intelligent opportunity ranking, "
        "smart alerts, what-if recovery simulator, and recovery outcome feedback loop. "
        "**SIMULATION/DEMO MODE** — No real payment actions are executed."
    ),
    version="3.0.0"
)


# ==========================================
# Create database when API starts
# ==========================================

create_database()
sync_smart_alerts()


# ==========================================
# Payment & Simulation input schemas
# ==========================================

class Payment(BaseModel):
    amount: float
    payment_method: str = "card"
    failure_reason: str
    previous_payments: int = 0
    previous_failures: int = 0
    days_since_last_payment: int = 0
    subscription: int = 0
    hour: int = 12
    is_weekend: int = 0
    payment_id: Optional[str] = None
    customer_id: Optional[str] = None
    retry_count: Optional[int] = 0


class SimulationRequest(BaseModel):
    amount: float
    payment_method: str = "card"
    failure_reason: str = "network_timeout"
    previous_payments: int = 5
    previous_failures: int = 1
    days_since_last_payment: int = 5
    subscription: int = 0
    hour: int = 14
    is_weekend: int = 0
    strategy: str = "AUTOMATIC_RETRY"


# ==========================================
# Recovery Outcome Pydantic Schemas
# ==========================================

class RecoveryOutcomeCreate(BaseModel):
    """
    Request body to record a recovery outcome.
    SIMULATION/DEMO MODE — no real payment action is executed.
    """
    payment_id: str = Field(..., description="Payment identifier")
    decision_id: Optional[int] = Field(None, description="ID of the linked recovery decision")
    outcome: str = Field(
        ...,
        description=f"Recovery outcome. Allowed: {sorted(VALID_OUTCOMES)}"
    )
    recovered_amount: float = Field(
        0.0,
        ge=0,
        description="Amount actually recovered. Cannot be negative or exceed payment amount."
    )
    recovery_time_seconds: Optional[float] = Field(
        None,
        ge=0,
        description="Time taken for recovery in seconds"
    )
    reason: Optional[str] = Field(None, description="Human-readable reason for this outcome")
    source: str = Field("SIMULATION", description="Data source: SIMULATION, DEMO, or PRODUCTION")

    class Config:
        json_schema_extra = {
            "example": {
                "payment_id": "PAY_001",
                "decision_id": 1,
                "outcome": "RECOVERED",
                "recovered_amount": 4999.0,
                "recovery_time_seconds": 185.0,
                "reason": "Customer completed payment after retry",
                "source": "SIMULATION"
            }
        }


class RecoveryOutcomeUpdate(BaseModel):
    """Fields allowed for updating a pending/attempted outcome."""
    reason: Optional[str] = None
    executed_action: Optional[str] = None
    strategy: Optional[str] = None
    failure_reason: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "executed_action": "RETRY_PAYMENT",
                "reason": "Updated after manual review"
            }
        }


class OutcomeResponse(BaseModel):
    """Standard response for recovery outcome creation/update."""
    success: bool
    outcome_id: Optional[int]
    payment_id: Optional[str]
    outcome: Optional[str]
    recovered_amount: Optional[float]
    updated_status: Optional[str]
    message: str


# ==========================================
# Home endpoint
# ==========================================

@app.get("/")
def home():
    return {
        "message": "RecoverAI API is running",
        "status": "healthy",
        "version": "3.0.0",
        "mode": "SIMULATION — No real payment actions executed"
    }


# ==========================================
# Recovery endpoint
# ==========================================

@app.post("/recover")
def recover_payment(payment: Payment):
    payment_data = payment.model_dump()

    # Run AI Recovery Agent
    result = recovery_agent(payment_data)

    # Save AI decision to database (automatically triggers alert evaluation)
    save_decision(result)

    return result


# ==========================================
# View recovery history
# ==========================================

@app.get("/decisions")
def decisions():
    rows = get_decisions()

    results = []
    for row in rows:
        results.append({
            "id": row.get("id"),
            "payment_id": row.get("payment_id"),
            "customer_id": row.get("customer_id"),
            "payment_amount": row.get("payment_amount"),
            "payment_method": row.get("payment_method", "card"),
            "failure_reason": row.get("failure_reason"),
            "recovery_probability": row.get("recovery_probability"),
            "expected_revenue": row.get("expected_revenue"),
            "risk_level": row.get("risk_level"),
            "recommended_action": row.get("recommended_action"),
            "retry_count": row.get("retry_count", 0),
            "revenue_opportunity_score": row.get("revenue_opportunity_score"),
            "priority_level": row.get("priority_level"),
            "reason": row.get("reason"),
            "explanation": row.get("explanation"),
            "timestamp": row.get("timestamp")
        })

    return {
        "total_decisions": len(results),
        "decisions": results
    }


# ==========================================
# Intelligent Revenue Opportunity Ranking Endpoint
# ==========================================

@app.get("/revenue-opportunities")
def revenue_opportunities(
    limit: Optional[int] = None,
    risk_level: Optional[str] = None,
    priority_level: Optional[str] = None,
    failure_reason: Optional[str] = None,
    recommended_action: Optional[str] = None,
    sort_by: str = "revenue_opportunity_score",
    sort_order: str = "desc"
):
    """
    Return failed payments ranked by their intelligent revenue recovery opportunity.
    """
    clean_risk = str(risk_level) if (risk_level is not None and not hasattr(risk_level, 'default')) else None
    clean_prio = str(priority_level) if (priority_level is not None and not hasattr(priority_level, 'default')) else None
    clean_reason = str(failure_reason) if (failure_reason is not None and not hasattr(failure_reason, 'default')) else None
    clean_action = str(recommended_action) if (recommended_action is not None and not hasattr(recommended_action, 'default')) else None
    clean_limit = int(limit) if (limit is not None and not hasattr(limit, 'default')) else None
    clean_sort = str(sort_by) if not hasattr(sort_by, 'default') else "revenue_opportunity_score"
    clean_order = str(sort_order) if not hasattr(sort_order, 'default') else "desc"

    opportunities = get_recovery_opportunities(
        limit=clean_limit,
        risk_level=clean_risk,
        priority_level=clean_prio,
        failure_reason=clean_reason,
        recommended_action=clean_action,
        sort_by=clean_sort,
        sort_order=clean_order
    )

    # Enrich with actual recovery outcome data
    outcomes = get_recovery_outcomes(limit=None)
    outcome_map: Dict[str, Dict] = {}
    for o in outcomes:
        pid = o.get("payment_id")
        if pid and (pid not in outcome_map or o.get("status") in ("SUCCESS", "FAILED")):
            outcome_map[pid] = o

    formatted_opportunities = []
    for opp in opportunities:
        pid = opp.get("payment_id")
        opp_outcome = outcome_map.get(pid, {})
        recovered_amount = float(opp_outcome.get("recovered_amount") or 0.0) if opp_outcome else 0.0
        payment_amount = float(opp.get("payment_amount") or 0.0)

        formatted_opportunities.append({
            "priority_rank": opp.get("priority_rank"),
            "payment_id": pid,
            "customer_id": opp.get("customer_id"),
            "payment_amount": payment_amount,
            "payment_method": opp.get("payment_method", "card"),
            "failure_reason": opp.get("failure_reason"),
            "recovery_probability": opp.get("recovery_probability"),
            "expected_revenue": opp.get("expected_revenue"),
            "revenue_opportunity_score": opp.get("revenue_opportunity_score"),
            "priority_level": opp.get("priority_level"),
            "risk_level": opp.get("risk_level"),
            "recommended_action": opp.get("recommended_action"),
            "retry_count": opp.get("retry_count", 0),
            "explanation": opp.get("explanation"),
            "reason": opp.get("reason"),
            "timestamp": opp.get("timestamp"),
            # Recovery outcome enrichment
            "recovery_status": opp_outcome.get("status") if opp_outcome else None,
            "recovery_outcome": opp_outcome.get("outcome") if opp_outcome else None,
            "recovered_amount": recovered_amount,
            "remaining_at_risk": max(0.0, payment_amount - recovered_amount)
        })

    return {
        "total_opportunities": len(formatted_opportunities),
        "opportunities": formatted_opportunities
    }


# ==========================================
# SMART ALERTS ENDPOINTS
# ==========================================

@app.get("/alerts")
def list_alerts(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    alert_type: Optional[str] = None,
    limit: Optional[int] = None
):
    """
    Retrieve active/recent Smart Alerts with deduplication and optional filters.
    """
    clean_status = str(status) if (status is not None and not hasattr(status, 'default')) else None
    clean_priority = str(priority) if (priority is not None and not hasattr(priority, 'default')) else None
    clean_type = str(alert_type) if (alert_type is not None and not hasattr(alert_type, 'default')) else None
    clean_limit = int(limit) if (limit is not None and not hasattr(limit, 'default')) else None

    # Sync any recent alerts from decisions
    sync_smart_alerts()

    alerts_list = get_alerts(
        status=clean_status,
        priority=clean_priority,
        alert_type=clean_type,
        limit=clean_limit
    )

    return alerts_list


@app.get("/alerts/summary")
def alerts_summary():
    """
    Retrieve aggregated alert counts and real-time revenue impact metrics.
    """
    sync_smart_alerts()
    summary = get_alerts_summary_metrics()
    return summary


@app.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str):
    """
    Acknowledge an open alert (OPEN -> ACKNOWLEDGED).
    """
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found."
        )

    try:
        updated = acknowledge_alert_db(alert_id)
        return {
            "message": f"Alert {alert_id} acknowledged successfully.",
            "alert": updated
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )


@app.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str):
    """
    Resolve an alert (ACKNOWLEDGED or OPEN -> RESOLVED).
    """
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found."
        )

    try:
        updated = resolve_alert_db(alert_id)
        return {
            "message": f"Alert {alert_id} resolved successfully.",
            "alert": updated
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )


# ==========================================
# RECOVERY SIMULATOR ENDPOINTS
# ==========================================

@app.post("/simulate-recovery")
def simulate_recovery(req: SimulationRequest):
    """
    Run what-if recovery strategy simulation for a payment scenario.
    Evaluates recovery probability, expected recovery, opportunity score,
    strategy compatibility under Recovery Agent rules, and identifies the best strategy.
    SIMULATION MODE — No real payment execution.
    """
    if req.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be greater than zero."
        )

    payment_data = req.model_dump()
    strategy = req.strategy.upper()

    try:
        sim_result = run_recovery_simulation(payment_data, selected_strategy=strategy)

        # Persist simulation run to SQLite history
        save_simulation(sim_result)

        return sim_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation error: {str(e)}"
        )


@app.get("/simulations")
def list_simulations(limit: Optional[int] = 50):
    """
    Retrieve recent simulation history runs.
    """
    clean_limit = int(limit) if limit is not None else 50
    sims = get_simulations(limit=clean_limit)
    return {
        "total_simulations": len(sims),
        "simulations": sims
    }


@app.get("/simulations/{simulation_id}")
def get_single_simulation(simulation_id: str):
    """
    Retrieve a specific simulation record by its ID.
    """
    sim = get_simulation_by_id(simulation_id)
    if not sim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation '{simulation_id}' not found."
        )
    return sim


# ==========================================
# AI Decision Explanation endpoint
# ==========================================

@app.get("/decisions/{decision_id}/explanation")
def decision_explanation(decision_id: int):
    rows = get_decisions()

    for row in rows:
        if row.get("id") == decision_id:
            explanation = generate_decision_explanation(row)
            return {
                "decision_id": decision_id,
                "decision": row,
                "explanation": explanation
            }

    return {"error": f"Decision #{decision_id} not found"}


# ==========================================
# RECOVERY OUTCOME ENDPOINTS
# ==========================================

@app.post("/recovery-outcomes", response_model=OutcomeResponse, status_code=201)
def create_recovery_outcome(req: RecoveryOutcomeCreate):
    """
    Record a recovery outcome for a payment.

    ⚠️ SIMULATION/DEMO MODE — This does NOT execute a real payment action.
    It records a simulated or demo recovery event in the RecoverAI database.

    Validates:
    - Outcome must be one of: RECOVERED, NOT_RECOVERED, CUSTOMER_ACTION_REQUIRED, RETRY_FAILED, EXPIRED
    - recovered_amount cannot be negative
    - recovered_amount cannot exceed payment amount (if linked to a decision)
    """
    outcome_upper = req.outcome.upper()
    if outcome_upper not in VALID_OUTCOMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid outcome '{req.outcome}'. Allowed values: {sorted(VALID_OUTCOMES)}"
        )

    if req.recovered_amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recovered_amount cannot be negative."
        )

    try:
        record = create_recovery_outcome_record(
            payment_id=req.payment_id,
            decision_id=req.decision_id,
            outcome=outcome_upper,
            recovered_amount=req.recovered_amount,
            recovery_time_seconds=req.recovery_time_seconds,
            reason=req.reason,
            actor="DEMO_USER",
            source=req.source
        )

        if not record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create recovery outcome record."
            )

        # Trigger Smart Alert evaluation
        try:
            from src.smart_alerts import evaluate_outcome_for_alerts, evaluate_system_outcome_alerts, build_alert_record
            cand_alerts = evaluate_outcome_for_alerts(record)
            for ca in cand_alerts:
                alert_rec = build_alert_record(ca)
                save_alert(alert_rec)
            # System-level outcome alerts
            all_outcomes = get_recovery_outcomes(limit=200)
            sys_alerts = evaluate_system_outcome_alerts(all_outcomes)
            for sa in sys_alerts:
                alert_rec = build_alert_record(sa)
                save_alert(alert_rec)
        except Exception:
            pass  # Alert failures never block the response

        return OutcomeResponse(
            success=True,
            outcome_id=record.get("id"),
            payment_id=record.get("payment_id"),
            outcome=record.get("outcome"),
            recovered_amount=record.get("recovered_amount"),
            updated_status=record.get("status"),
            message=f"Recovery outcome '{outcome_upper}' recorded successfully for payment '{req.payment_id}'."
        )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating recovery outcome: {str(e)}"
        )


@app.get("/recovery-outcomes")
def list_recovery_outcomes(
    payment_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: Optional[int] = 100
):
    """
    List recovery outcomes with optional filters.
    Supports filtering by payment_id, customer_id, status, outcome, and date range.
    """
    clean_limit = int(limit) if limit is not None else 100

    outcomes = get_recovery_outcomes(
        payment_id=payment_id,
        customer_id=customer_id,
        status=status,
        outcome=outcome,
        limit=clean_limit,
        date_from=date_from,
        date_to=date_to
    )

    return {
        "total_outcomes": len(outcomes),
        "outcomes": outcomes
    }


@app.get("/recovery-outcomes/{outcome_id}")
def get_recovery_outcome(outcome_id: int):
    """
    Retrieve a single recovery outcome by ID.
    """
    record = get_recovery_outcome_by_id(outcome_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery outcome #{outcome_id} not found."
        )
    return record


@app.put("/recovery-outcomes/{outcome_id}", response_model=OutcomeResponse)
def update_outcome(outcome_id: int, req: RecoveryOutcomeUpdate):
    """
    Update allowed fields of a pending/attempted recovery outcome.
    Cannot update terminal outcomes (SUCCESS, FAILED, CANCELLED).
    """
    record = get_recovery_outcome_by_id(outcome_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery outcome #{outcome_id} not found."
        )

    updates = {k: v for k, v in req.model_dump().items() if v is not None}

    try:
        updated = update_recovery_outcome(outcome_id, updates, actor="DEMO_USER")
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Update failed."
            )
        return OutcomeResponse(
            success=True,
            outcome_id=updated.get("id"),
            payment_id=updated.get("payment_id"),
            outcome=updated.get("outcome"),
            recovered_amount=updated.get("recovered_amount"),
            updated_status=updated.get("status"),
            message=f"Recovery outcome #{outcome_id} updated successfully."
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )


# ==========================================
# RECOVERY METRICS ENDPOINT
# ==========================================

@app.get("/recovery-metrics")
def recovery_metrics():
    """
    Return aggregated recovery performance metrics.
    All values computed from actual database records — never hardcoded.

    Recovery Rate = successful_recoveries / total_completed_outcomes * 100
    Revenue Remaining at Risk = total_revenue_at_risk - total_recovered
    """
    metrics = get_recovery_metrics()
    return metrics


# ==========================================
# RECOVERY PERFORMANCE BY STRATEGY
# ==========================================

@app.get("/recovery-performance")
def recovery_performance():
    """
    Return recovery performance grouped by recovery strategy/action.
    Includes: attempts, successful, failed, recovery_rate, revenue_recovered.
    """
    strategies = get_recovery_performance_by_strategy()
    return {
        "total_strategies": len(strategies),
        "strategies": strategies
    }


# ==========================================
# RECOVERY PERFORMANCE BY FAILURE REASON
# ==========================================

@app.get("/recovery-performance/failure-reasons")
def recovery_performance_failure_reasons():
    """
    Return recovery performance grouped by failure reason.
    Helps identify which failure types are easiest/hardest to recover.
    """
    reasons = get_recovery_performance_by_failure_reason()
    return {
        "total_failure_reasons": len(reasons),
        "failure_reasons": reasons
    }


# ==========================================
# CUSTOMER RECOVERY HISTORY
# ==========================================

@app.get("/customers/{customer_id}/recovery-history")
def customer_recovery_history(customer_id: str):
    """
    Return recovery history for a specific customer.
    Includes: total attempts, successes, failures, revenue recovered, recovery rate.
    """
    history = get_customer_recovery_history(customer_id)
    return history


# ==========================================
# FEEDBACK METRICS (AI Prediction vs Actual)
# ==========================================

@app.get("/feedback-metrics")
def feedback_metrics():
    """
    Return AI model prediction accuracy vs actual recovery outcomes.

    Clearly distinguishes:
    - MODEL PREDICTION (AI-predicted probability)
    - ACTUAL BUSINESS OUTCOME (real recovery result)

    prediction_correct: True if model predicted >= 50% and payment recovered, or < 50% and it didn't.

    NOTE: This system does NOT automatically retrain the model.
    Export /feedback-export to get training data for manual retraining.
    """
    return get_feedback_metrics()


# ==========================================
# FEEDBACK DATASET EXPORT
# ==========================================

@app.get("/feedback-export")
def feedback_export():
    """
    Export completed recovery outcomes as a training/feedback dataset.
    Combines original payment features + AI predictions + actual outcomes.

    Returns retraining feasibility (requires >= 50 completed records).
    Does NOT automatically retrain the model.
    """
    from src.feedback import export_feedback_dataset
    result = export_feedback_dataset()
    # Don't return full dataset in API response (could be large)
    dataset_preview = result.get("dataset", [])[:5]
    return {
        "record_count": result["record_count"],
        "retraining_feasible": result["retraining_feasible"],
        "message": result["message"],
        "min_required_for_retraining": result.get("min_required_for_retraining", 50),
        "dataset_preview": dataset_preview,
        "exported_at": result["exported_at"]
    }


# ==========================================
# AUDIT LOG ENDPOINT
# ==========================================

@app.get("/recovery-outcomes/{outcome_id}/audit")
def outcome_audit_log(outcome_id: int):
    """
    Retrieve the audit trail for a specific recovery outcome.
    Tracks all state transitions, actor, and timestamps.
    """
    record = get_recovery_outcome_by_id(outcome_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery outcome #{outcome_id} not found."
        )
    log = get_audit_log(outcome_id=outcome_id)
    return {
        "outcome_id": outcome_id,
        "payment_id": record.get("payment_id"),
        "current_status": record.get("status"),
        "audit_entries": log
    }


# ==========================================
# SEED DEMO DATA ENDPOINT
# ==========================================

@app.post("/seed-demo-outcomes")
def seed_demo_outcomes(force: bool = False):
    """
    Seed demo SIMULATION recovery outcome records for dashboard demonstration.

    ⚠️ DEMO ONLY — Creates clearly labeled SIMULATION records.
    Does NOT affect real customer or payment data.
    Does NOT automatically run at startup.
    """
    from src.seed_recovery_outcomes import seed_recovery_outcomes
    result = seed_recovery_outcomes(force=force)
    return result