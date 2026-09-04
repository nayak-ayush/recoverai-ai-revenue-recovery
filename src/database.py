import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# ==========================================
# Paths configuration
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
DATABASE = DATA_DIR / "recovery.db"

from src.ranking_engine import (
    calculate_opportunity_score,
    classify_priority_level,
    generate_opportunity_explanation,
    rank_opportunities
)


def get_connection():
    """Create and return a database connection with row factory."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    """
    Ensure all tables exist with full schema.
    Performs non-destructive schema migration if legacy columns exist.
    Tables: recovery_decisions, alerts, simulations, recovery_outcomes, recovery_audit_log
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # 1. Decisions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recovery_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT,
            customer_id TEXT,
            payment_amount REAL,
            payment_method TEXT,
            failure_reason TEXT,
            recovery_probability REAL,
            expected_revenue REAL,
            risk_level TEXT,
            recommended_action TEXT,
            retry_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'PENDING',
            actual_outcome TEXT DEFAULT 'PENDING',
            revenue_opportunity_score REAL,
            priority_level TEXT,
            reason TEXT,
            explanation TEXT,
            timestamp TEXT
        )
    """)

    # 2. Alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT UNIQUE,
            alert_type TEXT,
            priority TEXT,
            title TEXT,
            message TEXT,
            payment_id TEXT,
            customer_id TEXT,
            amount REAL,
            recovery_probability REAL,
            risk_level TEXT,
            opportunity_score REAL,
            recommended_action TEXT,
            expected_recovery REAL,
            status TEXT DEFAULT 'OPEN',
            dedup_key TEXT UNIQUE,
            why_explanation TEXT,
            recommended_step TEXT,
            created_at TEXT,
            acknowledged_at TEXT,
            resolved_at TEXT
        )
    """)

    # 3. Simulations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            simulation_id TEXT UNIQUE,
            created_at TEXT,
            amount REAL,
            payment_method TEXT,
            failure_reason TEXT,
            strategy TEXT,
            recovery_probability REAL,
            risk_level TEXT,
            expected_recovery REAL,
            opportunity_score REAL,
            recommended_action TEXT,
            strategy_allowed INTEGER DEFAULT 1,
            best_strategy TEXT,
            explanation TEXT
        )
    """)

    # 4. Recovery Outcomes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recovery_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT NOT NULL,
            customer_id TEXT,
            decision_id INTEGER,
            attempt_number INTEGER DEFAULT 1,
            recommended_action TEXT,
            executed_action TEXT,
            recovery_probability REAL,
            risk_level TEXT,
            payment_amount REAL,
            revenue_at_risk REAL,
            expected_recovery REAL,
            opportunity_score REAL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            outcome TEXT,
            recovered_amount REAL DEFAULT 0,
            recovery_time_seconds REAL,
            failure_reason TEXT,
            strategy TEXT,
            reason TEXT,
            source TEXT DEFAULT 'SIMULATION',
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # Create indexes for recovery_outcomes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ro_payment_id ON recovery_outcomes (payment_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ro_customer_id ON recovery_outcomes (customer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ro_status ON recovery_outcomes (status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ro_outcome ON recovery_outcomes (outcome)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ro_created_at ON recovery_outcomes (created_at)")

    # 5. Recovery Audit Log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recovery_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outcome_id INTEGER,
            payment_id TEXT,
            actor TEXT DEFAULT 'SYSTEM',
            action TEXT,
            old_status TEXT,
            new_status TEXT,
            old_outcome TEXT,
            new_outcome TEXT,
            recovered_amount REAL,
            notes TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ral_outcome_id ON recovery_audit_log (outcome_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ral_payment_id ON recovery_audit_log (payment_id)")

    connection.commit()

    # Perform safe migration for decisions table
    cursor.execute("PRAGMA table_info(recovery_decisions)")
    existing_dec_columns = {col[1] for col in cursor.fetchall()}

    required_dec_columns = {
        "payment_id": "TEXT",
        "customer_id": "TEXT",
        "payment_method": "TEXT DEFAULT 'card'",
        "retry_count": "INTEGER DEFAULT 0",
        "status": "TEXT DEFAULT 'PENDING'",
        "actual_outcome": "TEXT DEFAULT 'PENDING'",
        "revenue_opportunity_score": "REAL",
        "priority_level": "TEXT",
        "explanation": "TEXT"
    }

    for col_name, col_type in required_dec_columns.items():
        if col_name not in existing_dec_columns:
            cursor.execute(f"ALTER TABLE recovery_decisions ADD COLUMN {col_name} {col_type}")

    # Safe migration for recovery_outcomes table
    cursor.execute("PRAGMA table_info(recovery_outcomes)")
    existing_ro_columns = {col[1] for col in cursor.fetchall()}
    required_ro_columns = {
        "source": "TEXT DEFAULT 'SIMULATION'"
    }
    for col_name, col_type in required_ro_columns.items():
        if col_name not in existing_ro_columns:
            cursor.execute(f"ALTER TABLE recovery_outcomes ADD COLUMN {col_name} {col_type}")

    connection.commit()
    connection.close()


# ==========================================
# Recovery Decision Persistence & Queries
# ==========================================

def save_decision(result: Dict[str, Any]) -> int:
    """
    Save an AI recovery decision to the database and trigger real-time alert evaluation.
    """
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    payment_id = result.get("payment_id")
    customer_id = result.get("customer_id")
    payment_method = result.get("payment_method", "card")
    retry_count = result.get("retry_count", 0)
    status = result.get("status", "PENDING")
    actual_outcome = result.get("actual_outcome", "PENDING")
    score = result.get("revenue_opportunity_score")
    priority_level = result.get("priority_level")
    explanation = result.get("explanation")

    if score is None:
        score_data = calculate_opportunity_score(
            payment_amount=result["payment_amount"],
            recovery_probability=result["recovery_probability"],
            expected_revenue=result["expected_revenue"],
            recommended_action=result["recommended_action"],
            failure_reason=result["failure_reason"],
            retry_count=retry_count
        )
        score = score_data["revenue_opportunity_score"]
        priority_level = score_data["priority_level"]
        explanation = score_data["explanation"]

    cursor.execute("""
        INSERT INTO recovery_decisions (
            payment_id,
            customer_id,
            payment_amount,
            payment_method,
            failure_reason,
            recovery_probability,
            expected_revenue,
            risk_level,
            recommended_action,
            retry_count,
            status,
            actual_outcome,
            revenue_opportunity_score,
            priority_level,
            reason,
            explanation,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payment_id,
        customer_id,
        result["payment_amount"],
        payment_method,
        result["failure_reason"],
        result["recovery_probability"],
        result["expected_revenue"],
        result["risk_level"],
        result["recommended_action"],
        retry_count,
        status,
        actual_outcome,
        score,
        priority_level,
        result.get("reason", ""),
        explanation,
        result.get("timestamp", datetime.now().isoformat())
    ))

    inserted_id = cursor.lastrowid

    if not payment_id or not customer_id:
        final_pid = payment_id or f"PAY{inserted_id:05d}"
        final_cid = customer_id or f"CUST{inserted_id:04d}"
        cursor.execute("""
            UPDATE recovery_decisions
            SET payment_id = ?, customer_id = ?
            WHERE id = ?
        """, (final_pid, final_cid, inserted_id))
        result["payment_id"] = final_pid
        result["customer_id"] = final_cid

    connection.commit()
    connection.close()

    # Automatically evaluate for Smart Alerts
    try:
        from src.smart_alerts import evaluate_decision_for_alerts, build_alert_record
        cand_alerts = evaluate_decision_for_alerts(result)
        for ca in cand_alerts:
            alert_rec = build_alert_record(ca)
            save_alert(alert_rec)
    except Exception as e:
        pass

    return inserted_id


def get_decisions() -> List[Dict[str, Any]]:
    """
    Retrieve all recovery decisions from the database ordered by ID descending.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM recovery_decisions
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    connection.close()

    results = []
    for r in rows:
        row_dict = dict(r)
        if not row_dict.get("payment_id"):
            row_dict["payment_id"] = f"PAY{row_dict['id']:05d}"
        if not row_dict.get("customer_id"):
            row_dict["customer_id"] = f"CUST{row_dict['id']:04d}"
        if row_dict.get("revenue_opportunity_score") is None:
            score_data = calculate_opportunity_score(
                payment_amount=row_dict.get("payment_amount", 0.0),
                recovery_probability=row_dict.get("recovery_probability", 0.0),
                expected_revenue=row_dict.get("expected_revenue", 0.0),
                recommended_action=row_dict.get("recommended_action", "RETRY_PAYMENT"),
                failure_reason=row_dict.get("failure_reason", "network_timeout")
            )
            row_dict["revenue_opportunity_score"] = score_data["revenue_opportunity_score"]
            row_dict["priority_level"] = score_data["priority_level"]
            row_dict["explanation"] = score_data["explanation"]

        results.append(row_dict)

    return results


def get_recovery_opportunities(
    limit: Optional[int] = None,
    risk_level: Optional[str] = None,
    priority_level: Optional[str] = None,
    failure_reason: Optional[str] = None,
    recommended_action: Optional[str] = None,
    sort_by: str = "revenue_opportunity_score",
    sort_order: str = "desc"
) -> List[Dict[str, Any]]:
    """
    Fetch all decisions, rank them by revenue recovery opportunity,
    apply filters and limit, and return ranked opportunities list.
    """
    decisions = get_decisions()

    filtered = []
    for dec in decisions:
        if risk_level and risk_level.upper() != "ALL":
            if str(dec.get("risk_level", "")).upper() != risk_level.upper():
                continue

        if priority_level and priority_level.upper() != "ALL":
            if str(dec.get("priority_level", "")).upper() != priority_level.upper():
                continue

        if failure_reason and failure_reason.lower() != "all":
            if str(dec.get("failure_reason", "")).lower() != failure_reason.lower():
                continue

        if recommended_action and recommended_action.upper() != "ALL":
            if str(dec.get("recommended_action", "")).upper() != recommended_action.upper():
                continue

        filtered.append(dec)

    ranked = rank_opportunities(filtered, sort_by=sort_by, sort_order=sort_order)

    if limit is not None and limit > 0:
        ranked = ranked[:limit]

    return ranked


# ==============================================================================
# Smart Alerts Database Methods & Deduplication
# ==============================================================================

def save_alert(alert_dict: Dict[str, Any]) -> bool:
    """
    Save a new Smart Alert to the database.
    Strictly deduplicates: If an alert with the same dedup_key already exists
    in OPEN or ACKNOWLEDGED status, skips insertion and returns False.
    """
    dedup_key = alert_dict.get("dedup_key")
    
    connection = get_connection()
    cursor = connection.cursor()
    
    # Check if active alert with same dedup_key exists
    cursor.execute("""
        SELECT id, status FROM alerts
        WHERE dedup_key = ? AND status IN ('OPEN', 'ACKNOWLEDGED')
    """, (dedup_key,))
    
    existing = cursor.fetchone()
    if existing:
        connection.close()
        return False  # Deduplicated

    cursor.execute("""
        INSERT OR IGNORE INTO alerts (
            alert_id,
            alert_type,
            priority,
            title,
            message,
            payment_id,
            customer_id,
            amount,
            recovery_probability,
            risk_level,
            opportunity_score,
            recommended_action,
            expected_recovery,
            status,
            dedup_key,
            why_explanation,
            recommended_step,
            created_at,
            acknowledged_at,
            resolved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert_dict["alert_id"],
        alert_dict["alert_type"],
        alert_dict["priority"],
        alert_dict["title"],
        alert_dict["message"],
        alert_dict.get("payment_id"),
        alert_dict.get("customer_id"),
        alert_dict.get("amount", 0.0),
        alert_dict.get("recovery_probability", 0.0),
        alert_dict.get("risk_level", "MEDIUM"),
        alert_dict.get("opportunity_score", 0.0),
        alert_dict.get("recommended_action", "STOP_AUTOMATIC_RECOVERY"),
        alert_dict.get("expected_recovery", 0.0),
        alert_dict.get("status", "OPEN"),
        dedup_key,
        alert_dict.get("why_explanation", ""),
        alert_dict.get("recommended_step", ""),
        alert_dict.get("created_at", datetime.now().isoformat()),
        alert_dict.get("acknowledged_at"),
        alert_dict.get("resolved_at")
    ))
    
    connection.commit()
    connection.close()
    return True


def get_alerts(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    alert_type: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fetch Smart Alerts with optional filters.
    """
    connection = get_connection()
    cursor = connection.cursor()

    query = "SELECT * FROM alerts WHERE 1=1"
    params = []

    if status and status.upper() != "ALL":
        query += " AND status = ?"
        params.append(status.upper())

    if priority and priority.upper() != "ALL":
        query += " AND priority = ?"
        params.append(priority.upper())

    if alert_type and alert_type.upper() != "ALL":
        query += " AND alert_type = ?"
        params.append(alert_type.upper())

    # Order by priority weight (CRITICAL first) then created_at DESC
    query += """
        ORDER BY 
            CASE priority 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                ELSE 4 
            END ASC,
            id DESC
    """

    if limit and limit > 0:
        query += f" LIMIT {int(limit)}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    connection.close()

    return [dict(r) for r in rows]


def get_alert_by_id(alert_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single alert by its alert_id."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None


def acknowledge_alert_db(alert_id: str) -> Optional[Dict[str, Any]]:
    """
    Transition alert status from OPEN -> ACKNOWLEDGED.
    Returns the updated alert dict, or None if alert does not exist or transition is invalid.
    """
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
    row = cursor.fetchone()
    if not row:
        connection.close()
        return None
        
    current_status = row["status"]
    if current_status != "OPEN":
        connection.close()
        raise ValueError(f"Cannot acknowledge alert in '{current_status}' status. Only OPEN alerts can be acknowledged.")
        
    now_iso = datetime.now().isoformat()
    cursor.execute("""
        UPDATE alerts
        SET status = 'ACKNOWLEDGED', acknowledged_at = ?
        WHERE alert_id = ?
    """, (now_iso, alert_id))
    
    connection.commit()
    
    cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
    updated_row = cursor.fetchone()
    connection.close()
    
    return dict(updated_row) if updated_row else None


def resolve_alert_db(alert_id: str) -> Optional[Dict[str, Any]]:
    """
    Transition alert status to RESOLVED (from ACKNOWLEDGED or OPEN).
    Returns the updated alert dict, or None if alert does not exist or already resolved.
    """
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
    row = cursor.fetchone()
    if not row:
        connection.close()
        return None
        
    current_status = row["status"]
    if current_status == "RESOLVED":
        connection.close()
        raise ValueError("Alert is already in RESOLVED status.")
        
    now_iso = datetime.now().isoformat()
    cursor.execute("""
        UPDATE alerts
        SET status = 'RESOLVED', resolved_at = ?
        WHERE alert_id = ?
    """, (now_iso, alert_id))
    
    connection.commit()
    
    cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
    updated_row = cursor.fetchone()
    connection.close()
    
    return dict(updated_row) if updated_row else None


def get_alerts_summary_metrics() -> Dict[str, Any]:
    """
    Compute total counts and real financial impact metrics from active alerts.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM alerts")
    rows = cursor.fetchall()
    connection.close()

    total = len(rows)
    crit = sum(1 for r in rows if r["priority"] == "CRITICAL")
    high = sum(1 for r in rows if r["priority"] == "HIGH")
    med = sum(1 for r in rows if r["priority"] == "MEDIUM")
    low = sum(1 for r in rows if r["priority"] == "LOW")

    open_c = sum(1 for r in rows if r["status"] == "OPEN")
    ack_c = sum(1 for r in rows if r["status"] == "ACKNOWLEDGED")
    res_c = sum(1 for r in rows if r["status"] == "RESOLVED")

    # Financial impact of active alerts (OPEN and ACKNOWLEDGED)
    active_rows = [r for r in rows if r["status"] in ("OPEN", "ACKNOWLEDGED")]
    rev_at_risk = sum(float(r["amount"]) for r in active_rows)
    pot_recovery = sum(float(r["expected_recovery"]) for r in active_rows)
    crit_risk = sum(float(r["amount"]) for r in active_rows if r["priority"] == "CRITICAL")

    return {
        "total_alerts": total,
        "critical_alerts": crit,
        "high_alerts": high,
        "medium_alerts": med,
        "low_alerts": low,
        "open_alerts": open_c,
        "acknowledged_alerts": ack_c,
        "resolved_alerts": res_c,
        "revenue_at_risk": round(rev_at_risk, 2),
        "potential_recovery": round(pot_recovery, 2),
        "critical_revenue_at_risk": round(crit_risk, 2)
    }


def sync_smart_alerts():
    """
    Scan all historical decisions and macro conditions, generate and save any missing alerts.
    Safely deduplicates.
    """
    from src.smart_alerts import evaluate_decision_for_alerts, evaluate_system_alerts, build_alert_record
    
    decisions = get_decisions()
    
    # 1. Evaluate per-decision alerts
    for dec in decisions:
        cand_alerts = evaluate_decision_for_alerts(dec)
        for ca in cand_alerts:
            alert_rec = build_alert_record(ca)
            save_alert(alert_rec)
            
    # 2. Evaluate system macro alerts
    sys_alerts = evaluate_system_alerts(decisions)
    for sa in sys_alerts:
        alert_rec = build_alert_record(sa)
        save_alert(alert_rec)


# ==============================================================================
# Recovery Simulation Persistence & Queries
# ==============================================================================

def save_simulation(sim_dict: Dict[str, Any]) -> str:
    """
    Save a simulation record to the SQLite database.
    Returns the simulation_id.
    """
    import uuid
    connection = get_connection()
    cursor = connection.cursor()

    sim_id = sim_dict.get("simulation_id") or f"SIM-{uuid.uuid4().hex[:8].upper()}"
    created_at = sim_dict.get("created_at") or datetime.now().isoformat()
    amount = float(sim_dict.get("amount", 0.0))
    payment_method = str(sim_dict.get("payment_method", "card"))
    failure_reason = str(sim_dict.get("failure_reason", "network_timeout"))
    strategy = str(sim_dict.get("strategy", "AUTOMATIC_RETRY"))
    prob = float(sim_dict.get("recovery_probability", 0.0))
    risk_level = str(sim_dict.get("risk_level", "MEDIUM"))
    expected_recovery = float(sim_dict.get("expected_recovery", 0.0))
    opportunity_score = float(sim_dict.get("opportunity_score", 0.0))
    action = str(sim_dict.get("recommended_action", "RETRY_PAYMENT"))
    strategy_allowed = 1 if sim_dict.get("strategy_allowed", True) else 0
    best_strategy = str(sim_dict.get("best_strategy", strategy))
    explanation = str(sim_dict.get("explanation", ""))

    cursor.execute("""
        INSERT INTO simulations (
            simulation_id,
            created_at,
            amount,
            payment_method,
            failure_reason,
            strategy,
            recovery_probability,
            risk_level,
            expected_recovery,
            opportunity_score,
            recommended_action,
            strategy_allowed,
            best_strategy,
            explanation
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sim_id,
        created_at,
        amount,
        payment_method,
        failure_reason,
        strategy,
        prob,
        risk_level,
        expected_recovery,
        opportunity_score,
        action,
        strategy_allowed,
        best_strategy,
        explanation
    ))

    connection.commit()
    connection.close()
    return sim_id


def get_simulations(limit: Optional[int] = 50) -> List[Dict[str, Any]]:
    """Retrieve recent simulation runs ordered by ID descending."""
    connection = get_connection()
    cursor = connection.cursor()

    query = "SELECT * FROM simulations ORDER BY id DESC"
    if limit and limit > 0:
        query += f" LIMIT {int(limit)}"

    cursor.execute(query)
    rows = cursor.fetchall()
    connection.close()

    results = []
    for r in rows:
        row_dict = dict(r)
        row_dict["strategy_allowed"] = bool(row_dict.get("strategy_allowed", 1))
        results.append(row_dict)

    return results


def get_simulation_by_id(simulation_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single simulation record by its simulation_id."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM simulations WHERE simulation_id = ?", (simulation_id,))
    row = cursor.fetchone()
    connection.close()
    if row:
        d = dict(row)
        d["strategy_allowed"] = bool(d.get("strategy_allowed", 1))
        return d
    return None


# ==============================================================================
# Recovery Outcomes Persistence & Queries
# ==============================================================================

VALID_STATUSES = {"PENDING", "ATTEMPTED", "SUCCESS", "FAILED", "CANCELLED"}
VALID_OUTCOMES = {"RECOVERED", "NOT_RECOVERED", "CUSTOMER_ACTION_REQUIRED", "RETRY_FAILED", "EXPIRED"}

# Allowed state transitions
STATUS_TRANSITIONS = {
    "PENDING": {"ATTEMPTED", "CANCELLED"},
    "ATTEMPTED": {"SUCCESS", "FAILED", "CANCELLED"},
    "SUCCESS": set(),   # Terminal state
    "FAILED": set(),    # Terminal state
    "CANCELLED": set()  # Terminal state
}


def record_recovery_attempt(
    payment_id: str,
    decision_id: Optional[int] = None,
    recommended_action: Optional[str] = None,
    executed_action: Optional[str] = None,
    recovery_probability: Optional[float] = None,
    risk_level: Optional[str] = None,
    payment_amount: Optional[float] = None,
    expected_recovery: Optional[float] = None,
    opportunity_score: Optional[float] = None,
    revenue_at_risk: Optional[float] = None,
    failure_reason: Optional[str] = None,
    strategy: Optional[str] = None,
    reason: Optional[str] = None,
    customer_id: Optional[str] = None,
    attempt_number: int = 1,
    source: str = "SIMULATION",
    actor: str = "SYSTEM"
) -> int:
    """
    Create a new recovery attempt record with PENDING status.
    Returns the new outcome ID.
    """
    connection = get_connection()
    cursor = connection.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO recovery_outcomes (
            payment_id, customer_id, decision_id, attempt_number,
            recommended_action, executed_action, recovery_probability,
            risk_level, payment_amount, revenue_at_risk, expected_recovery,
            opportunity_score, status, failure_reason, strategy, reason,
            source, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, ?)
    """, (
        payment_id, customer_id, decision_id, attempt_number,
        recommended_action, executed_action, recovery_probability,
        risk_level, payment_amount, revenue_at_risk if revenue_at_risk is not None else payment_amount,
        expected_recovery, opportunity_score, failure_reason, strategy, reason,
        source, now, now
    ))

    outcome_id = cursor.lastrowid

    # Audit log
    cursor.execute("""
        INSERT INTO recovery_audit_log (outcome_id, payment_id, actor, action, old_status, new_status, created_at)
        VALUES (?, ?, ?, 'CREATE', NULL, 'PENDING', ?)
    """, (outcome_id, payment_id, actor, now))

    connection.commit()
    connection.close()
    return outcome_id


def save_recovery_outcome(
    outcome_id: int,
    outcome: str,
    recovered_amount: float = 0.0,
    recovery_time_seconds: Optional[float] = None,
    failure_reason: Optional[str] = None,
    reason: Optional[str] = None,
    actor: str = "DEMO_USER"
) -> Optional[Dict[str, Any]]:
    """
    Record the final outcome of a recovery attempt.
    Transitions status from ATTEMPTED -> SUCCESS or FAILED.
    Returns the updated record or None if not found / invalid transition.
    """
    outcome_upper = outcome.upper()
    if outcome_upper not in VALID_OUTCOMES:
        raise ValueError(f"Invalid outcome '{outcome}'. Must be one of: {VALID_OUTCOMES}")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM recovery_outcomes WHERE id = ?", (outcome_id,))
    row = cursor.fetchone()
    if not row:
        connection.close()
        return None

    row_dict = dict(row)
    current_status = row_dict["status"]

    # Determine new status from outcome
    if outcome_upper == "RECOVERED":
        new_status = "SUCCESS"
    else:
        new_status = "FAILED"

    # Validate state transition
    allowed = STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        connection.close()
        raise ValueError(
            f"Cannot transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {allowed}"
        )

    # Validate recovered_amount
    payment_amount = row_dict.get("payment_amount") or 0.0
    if recovered_amount < 0:
        connection.close()
        raise ValueError("recovered_amount cannot be negative.")
    if payment_amount > 0 and recovered_amount > payment_amount:
        connection.close()
        raise ValueError(
            f"recovered_amount ({recovered_amount}) cannot exceed payment_amount ({payment_amount})."
        )

    now = datetime.now().isoformat()
    old_outcome = row_dict.get("outcome")

    cursor.execute("""
        UPDATE recovery_outcomes
        SET status = ?, outcome = ?, recovered_amount = ?,
            recovery_time_seconds = ?, failure_reason = COALESCE(?, failure_reason),
            reason = COALESCE(?, reason), updated_at = ?
        WHERE id = ?
    """, (new_status, outcome_upper, recovered_amount, recovery_time_seconds,
           failure_reason, reason, now, outcome_id))

    # Audit log
    cursor.execute("""
        INSERT INTO recovery_audit_log (
            outcome_id, payment_id, actor, action, old_status, new_status,
            old_outcome, new_outcome, recovered_amount, created_at
        ) VALUES (?, ?, ?, 'UPDATE_OUTCOME', ?, ?, ?, ?, ?, ?)
    """, (outcome_id, row_dict["payment_id"], actor, current_status, new_status,
           old_outcome, outcome_upper, recovered_amount, now))

    connection.commit()

    cursor.execute("SELECT * FROM recovery_outcomes WHERE id = ?", (outcome_id,))
    updated = cursor.fetchone()
    connection.close()

    return dict(updated) if updated else None


def advance_outcome_to_attempted(outcome_id: int, actor: str = "SYSTEM") -> Optional[Dict[str, Any]]:
    """
    Move a PENDING outcome to ATTEMPTED status.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM recovery_outcomes WHERE id = ?", (outcome_id,))
    row = cursor.fetchone()
    if not row:
        connection.close()
        return None

    row_dict = dict(row)
    if row_dict["status"] != "PENDING":
        connection.close()
        raise ValueError(f"Can only advance PENDING outcomes to ATTEMPTED. Current status: {row_dict['status']}")

    now = datetime.now().isoformat()
    cursor.execute("""
        UPDATE recovery_outcomes SET status = 'ATTEMPTED', updated_at = ? WHERE id = ?
    """, (now, outcome_id))

    cursor.execute("""
        INSERT INTO recovery_audit_log (outcome_id, payment_id, actor, action, old_status, new_status, created_at)
        VALUES (?, ?, ?, 'ADVANCE_TO_ATTEMPTED', 'PENDING', 'ATTEMPTED', ?)
    """, (outcome_id, row_dict["payment_id"], actor, now))

    connection.commit()
    cursor.execute("SELECT * FROM recovery_outcomes WHERE id = ?", (outcome_id,))
    updated = cursor.fetchone()
    connection.close()
    return dict(updated) if updated else None


def create_recovery_outcome_record(
    payment_id: str,
    decision_id: Optional[int],
    outcome: str,
    recovered_amount: float = 0.0,
    recovery_time_seconds: Optional[float] = None,
    reason: Optional[str] = None,
    actor: str = "DEMO_USER",
    source: str = "SIMULATION"
) -> Dict[str, Any]:
    """
    High-level helper: Look up decision info, create a recovery attempt,
    advance it to ATTEMPTED, then record the final outcome in one call.
    Returns the final outcome record.
    """
    # Fetch decision info for enrichment
    decision_data: Dict[str, Any] = {}
    if decision_id is not None:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM recovery_decisions WHERE id = ?", (decision_id,))
        row = cursor.fetchone()
        connection.close()
        if row:
            decision_data = dict(row)

    payment_amount = decision_data.get("payment_amount", 0.0)
    if payment_amount is None:
        payment_amount = 0.0

    # Validate outcome
    outcome_upper = outcome.upper()
    if outcome_upper not in VALID_OUTCOMES:
        raise ValueError(f"Invalid outcome. Must be one of: {sorted(VALID_OUTCOMES)}")

    # Validate recovered_amount
    if recovered_amount < 0:
        raise ValueError("recovered_amount cannot be negative.")
    if payment_amount > 0 and recovered_amount > payment_amount:
        raise ValueError(
            f"recovered_amount ({recovered_amount}) exceeds payment_amount ({payment_amount})."
        )

    # Create attempt
    attempt_id = record_recovery_attempt(
        payment_id=payment_id,
        decision_id=decision_id,
        recommended_action=decision_data.get("recommended_action"),
        executed_action=decision_data.get("recommended_action"),
        recovery_probability=decision_data.get("recovery_probability"),
        risk_level=decision_data.get("risk_level"),
        payment_amount=payment_amount,
        expected_recovery=decision_data.get("expected_revenue"),
        opportunity_score=decision_data.get("revenue_opportunity_score"),
        revenue_at_risk=payment_amount,
        failure_reason=decision_data.get("failure_reason"),
        strategy=decision_data.get("recommended_action"),
        reason=reason,
        customer_id=decision_data.get("customer_id"),
        source=source,
        actor=actor
    )

    # Advance to ATTEMPTED
    advance_outcome_to_attempted(attempt_id, actor=actor)

    # Record final outcome
    updated = save_recovery_outcome(
        outcome_id=attempt_id,
        outcome=outcome_upper,
        recovered_amount=recovered_amount,
        recovery_time_seconds=recovery_time_seconds,
        reason=reason,
        actor=actor
    )

    return updated or {}


def get_recovery_outcomes(
    payment_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: Optional[int] = 100,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fetch recovery outcomes with optional filters."""
    connection = get_connection()
    cursor = connection.cursor()

    query = "SELECT * FROM recovery_outcomes WHERE 1=1"
    params: List[Any] = []

    if payment_id:
        query += " AND payment_id = ?"
        params.append(payment_id)
    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
    if status and status.upper() != "ALL":
        query += " AND status = ?"
        params.append(status.upper())
    if outcome and outcome.upper() != "ALL":
        query += " AND outcome = ?"
        params.append(outcome.upper())
    if date_from:
        query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= ?"
        params.append(date_to)

    query += " ORDER BY id DESC"

    if limit and limit > 0:
        query += f" LIMIT {int(limit)}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]


def get_recovery_outcome_by_id(outcome_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single recovery outcome by its ID."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM recovery_outcomes WHERE id = ?", (outcome_id,))
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None


def update_recovery_outcome(
    outcome_id: int,
    updates: Dict[str, Any],
    actor: str = "DEMO_USER"
) -> Optional[Dict[str, Any]]:
    """
    Safely update a pending/attempted recovery outcome.
    Only allowed fields: reason, executed_action, strategy, failure_reason.
    Does NOT allow changing status/outcome directly (use save_recovery_outcome).
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM recovery_outcomes WHERE id = ?", (outcome_id,))
    row = cursor.fetchone()
    if not row:
        connection.close()
        return None

    row_dict = dict(row)
    if row_dict["status"] not in ("PENDING", "ATTEMPTED"):
        connection.close()
        raise ValueError(f"Cannot update a recovery outcome in '{row_dict['status']}' status.")

    allowed_fields = {"reason", "executed_action", "strategy", "failure_reason"}
    set_clauses = []
    values = []
    for field in allowed_fields:
        if field in updates:
            set_clauses.append(f"{field} = ?")
            values.append(updates[field])

    if not set_clauses:
        connection.close()
        return row_dict

    now = datetime.now().isoformat()
    set_clauses.append("updated_at = ?")
    values.append(now)
    values.append(outcome_id)

    cursor.execute(f"UPDATE recovery_outcomes SET {', '.join(set_clauses)} WHERE id = ?", values)

    cursor.execute("""
        INSERT INTO recovery_audit_log (outcome_id, payment_id, actor, action, old_status, new_status, notes, created_at)
        VALUES (?, ?, ?, 'FIELD_UPDATE', ?, ?, ?, ?)
    """, (outcome_id, row_dict["payment_id"], actor, row_dict["status"], row_dict["status"],
           str(list(updates.keys())), now))

    connection.commit()
    cursor.execute("SELECT * FROM recovery_outcomes WHERE id = ?", (outcome_id,))
    updated = cursor.fetchone()
    connection.close()
    return dict(updated) if updated else None


def get_recovery_metrics() -> Dict[str, Any]:
    """
    Compute recovery metrics summary from actual database records.
    All values are aggregated via SQL — never hardcoded.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) AS total_attempts,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful_recoveries,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_recoveries,
            SUM(CASE WHEN status IN ('SUCCESS', 'FAILED') THEN 1 ELSE 0 END) AS completed_outcomes,
            SUM(COALESCE(revenue_at_risk, payment_amount, 0)) AS total_revenue_at_risk,
            SUM(COALESCE(recovered_amount, 0)) AS total_recovered,
            AVG(CASE WHEN recovery_time_seconds IS NOT NULL THEN recovery_time_seconds END) AS avg_recovery_time,
            AVG(CASE WHEN status = 'SUCCESS' THEN COALESCE(recovered_amount, 0) END) AS avg_recovered_amount
        FROM recovery_outcomes
    """)

    row = cursor.fetchone()
    connection.close()

    if not row:
        return {
            "total_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "recovery_rate": 0.0,
            "revenue_at_risk": 0.0,
            "revenue_recovered": 0.0,
            "revenue_remaining_at_risk": 0.0,
            "average_recovery_time_seconds": None,
            "average_recovered_amount": None
        }

    total = row["total_attempts"] or 0
    successful = row["successful_recoveries"] or 0
    failed = row["failed_recoveries"] or 0
    completed = row["completed_outcomes"] or 0
    revenue_at_risk = round(float(row["total_revenue_at_risk"] or 0), 2)
    revenue_recovered = round(float(row["total_recovered"] or 0), 2)
    avg_time = round(float(row["avg_recovery_time"]), 2) if row["avg_recovery_time"] is not None else None
    avg_amount = round(float(row["avg_recovered_amount"]), 2) if row["avg_recovered_amount"] is not None else None

    recovery_rate = round((successful / completed * 100), 2) if completed > 0 else 0.0

    return {
        "total_attempts": total,
        "successful_recoveries": successful,
        "failed_recoveries": failed,
        "recovery_rate": recovery_rate,
        "revenue_at_risk": revenue_at_risk,
        "revenue_recovered": revenue_recovered,
        "revenue_remaining_at_risk": round(max(0.0, revenue_at_risk - revenue_recovered), 2),
        "average_recovery_time_seconds": avg_time,
        "average_recovered_amount": avg_amount
    }


def get_recovery_performance_by_strategy() -> List[Dict[str, Any]]:
    """
    Group recovery outcomes by strategy/recommended_action and compute performance metrics.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COALESCE(strategy, recommended_action, 'UNKNOWN') AS strategy,
            COUNT(*) AS attempts,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
            SUM(CASE WHEN status IN ('SUCCESS', 'FAILED') THEN 1 ELSE 0 END) AS completed,
            SUM(COALESCE(recovered_amount, 0)) AS revenue_recovered,
            SUM(COALESCE(revenue_at_risk, payment_amount, 0)) AS revenue_at_risk
        FROM recovery_outcomes
        GROUP BY COALESCE(strategy, recommended_action, 'UNKNOWN')
        ORDER BY revenue_recovered DESC
    """)

    rows = cursor.fetchall()
    connection.close()

    results = []
    for r in rows:
        completed = r["completed"] or 0
        successful = r["successful"] or 0
        recovery_rate = round((successful / completed * 100), 2) if completed > 0 else 0.0
        results.append({
            "strategy": r["strategy"],
            "attempts": r["attempts"] or 0,
            "successful": successful,
            "failed": r["failed"] or 0,
            "recovery_rate": recovery_rate,
            "revenue_recovered": round(float(r["revenue_recovered"] or 0), 2),
            "revenue_at_risk": round(float(r["revenue_at_risk"] or 0), 2)
        })
    return results


def get_recovery_performance_by_failure_reason() -> List[Dict[str, Any]]:
    """
    Group recovery outcomes by failure_reason and compute performance metrics.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COALESCE(failure_reason, 'UNKNOWN') AS failure_reason,
            COUNT(*) AS attempts,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS successful,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
            SUM(CASE WHEN status IN ('SUCCESS', 'FAILED') THEN 1 ELSE 0 END) AS completed,
            SUM(COALESCE(recovered_amount, 0)) AS revenue_recovered,
            SUM(COALESCE(revenue_at_risk, payment_amount, 0)) AS revenue_at_risk
        FROM recovery_outcomes
        GROUP BY COALESCE(failure_reason, 'UNKNOWN')
        ORDER BY revenue_recovered DESC
    """)

    rows = cursor.fetchall()
    connection.close()

    results = []
    for r in rows:
        completed = r["completed"] or 0
        successful = r["successful"] or 0
        recovery_rate = round((successful / completed * 100), 2) if completed > 0 else 0.0
        results.append({
            "failure_reason": r["failure_reason"],
            "attempts": r["attempts"] or 0,
            "successful": successful,
            "failed": r["failed"] or 0,
            "recovery_rate": recovery_rate,
            "revenue_recovered": round(float(r["revenue_recovered"] or 0), 2),
            "revenue_at_risk": round(float(r["revenue_at_risk"] or 0), 2)
        })
    return results


def get_customer_recovery_history(customer_id: str) -> Dict[str, Any]:
    """
    Return a summary of recovery history for a given customer_id.
    """
    outcomes = get_recovery_outcomes(customer_id=customer_id, limit=None)

    total = len(outcomes)
    successful = sum(1 for o in outcomes if o["status"] == "SUCCESS")
    failed = sum(1 for o in outcomes if o["status"] == "FAILED")
    revenue_recovered = sum(float(o.get("recovered_amount") or 0) for o in outcomes)
    revenue_at_risk = sum(float(o.get("revenue_at_risk") or o.get("payment_amount") or 0) for o in outcomes)
    completed = successful + failed
    recovery_rate = round((successful / completed * 100), 2) if completed > 0 else 0.0

    return {
        "customer_id": customer_id,
        "total_attempts": total,
        "successful_recoveries": successful,
        "failed_recoveries": failed,
        "recovery_rate": recovery_rate,
        "revenue_recovered": round(revenue_recovered, 2),
        "revenue_at_risk": round(revenue_at_risk, 2),
        "recovery_history": outcomes
    }


def get_feedback_metrics() -> Dict[str, Any]:
    """
    Compare AI predictions against actual recovery outcomes.
    Prediction accuracy = fraction where prediction_correct is True.
    prediction_correct = True when:
      - outcome is RECOVERED and recovery_probability >= 0.5
      - outcome is NOT RECOVERED and recovery_probability < 0.5
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Completed outcomes with known recovery_probability
    cursor.execute("""
        SELECT
            recovery_probability,
            outcome,
            recovered_amount,
            expected_recovery,
            payment_amount
        FROM recovery_outcomes
        WHERE status IN ('SUCCESS', 'FAILED')
          AND recovery_probability IS NOT NULL
    """)
    rows = cursor.fetchall()
    connection.close()

    total = len(rows)
    if total == 0:
        return {
            "total_predictions": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
            "prediction_accuracy": 0.0,
            "average_predicted_probability": 0.0,
            "actual_recovery_rate": 0.0,
            "probability_calibration_gap": 0.0,
            "predicted_revenue": 0.0,
            "actual_recovered_revenue": 0.0,
            "prediction_revenue_error": 0.0,
            "note": "No completed outcomes with predictions available."
        }

    correct = 0
    total_pred_prob = 0.0
    actual_successes = 0
    predicted_revenue = 0.0
    actual_revenue = 0.0

    for r in rows:
        prob = float(r["recovery_probability"] or 0.0)
        outcome = str(r["outcome"] or "").upper()
        is_recovered = outcome == "RECOVERED"
        recovered_amount = float(r["recovered_amount"] or 0.0)
        expected = float(r["expected_recovery"] or 0.0)

        # Prediction correct if model predicted > 50% and it recovered, or < 50% and it didn't
        if (prob >= 0.5 and is_recovered) or (prob < 0.5 and not is_recovered):
            correct += 1

        if is_recovered:
            actual_successes += 1

        total_pred_prob += prob
        predicted_revenue += expected
        actual_revenue += recovered_amount

    avg_pred_prob = round(total_pred_prob / total, 4)
    actual_recovery_rate = round((actual_successes / total * 100), 2)
    prediction_accuracy = round((correct / total * 100), 2)
    calibration_gap = round(abs((avg_pred_prob * 100) - actual_recovery_rate), 2)

    return {
        "total_predictions": total,
        "successful_predictions": actual_successes,
        "failed_predictions": total - actual_successes,
        "prediction_accuracy": prediction_accuracy,
        "average_predicted_probability": round(avg_pred_prob * 100, 2),
        "actual_recovery_rate": actual_recovery_rate,
        "probability_calibration_gap": calibration_gap,
        "predicted_revenue": round(predicted_revenue, 2),
        "actual_recovered_revenue": round(actual_revenue, 2),
        "prediction_revenue_error": round(abs(predicted_revenue - actual_revenue), 2)
    }


def get_audit_log(outcome_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch audit log entries, optionally filtered by outcome_id."""
    connection = get_connection()
    cursor = connection.cursor()
    if outcome_id is not None:
        cursor.execute(
            "SELECT * FROM recovery_audit_log WHERE outcome_id = ? ORDER BY id DESC",
            (outcome_id,)
        )
    else:
        cursor.execute("SELECT * FROM recovery_audit_log ORDER BY id DESC LIMIT 200")
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    create_database()
    sync_smart_alerts()
    print("Database, Smart Alerts, and Simulation schema synchronized successfully!")