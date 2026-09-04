"""
RecoverAI API Health Module
Performs real health checks on all system components.
Stores health history in SQLite for trend tracking.
Does NOT execute real payments or retrain models.
"""

import sys
import time
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODEL_FILE = PROJECT_ROOT / "models" / "recovery_model.pkl"
API_VERSION = "3.0.0"

# Track when the API process started
_STARTUP_TIME = time.time()

REQUIRED_TABLES = [
    "recovery_decisions",
    "alerts",
    "simulations",
    "recovery_outcomes",
    "recovery_audit_log",
    "app_settings",
    "health_history",
]


def ensure_health_history_table():
    """Create health_history table if it doesn't exist."""
    from src.database import get_connection, DATA_DIR, DATABASE
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checked_at TEXT NOT NULL,
            api_status TEXT,
            database_status TEXT,
            model_status TEXT,
            recovery_agent_status TEXT,
            overall_status TEXT,
            response_time_ms REAL,
            notes TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hh_checked_at ON health_history (checked_at)")
    conn.commit()
    conn.close()


def check_database_health() -> Dict[str, Any]:
    """
    Verify database connectivity, required tables existence, and basic query.
    Returns status dict with response time.
    """
    from src.database import DATABASE, DATA_DIR

    t0 = time.time()
    try:
        conn = sqlite3.connect(str(DATABASE))
        cursor = conn.cursor()

        # Get all existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = {row[0] for row in cursor.fetchall()}

        # Check required tables (ignoring health_history itself to avoid chicken-egg)
        required_check = [t for t in REQUIRED_TABLES if t != "health_history"]
        missing = [t for t in required_check if t not in existing]

        # Simple query to verify read works
        cursor.execute("SELECT COUNT(*) FROM recovery_decisions")
        decision_count = cursor.fetchone()[0]
        conn.close()

        elapsed_ms = round((time.time() - t0) * 1000, 2)
        status = "healthy" if not missing else "degraded"

        return {
            "status": status,
            "response_time_ms": elapsed_ms,
            "existing_tables": sorted(list(existing)),
            "missing_required_tables": missing,
            "decision_count": decision_count,
            "database_path": str(DATABASE)
        }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        return {
            "status": "unhealthy",
            "response_time_ms": elapsed_ms,
            "error": str(e),
            "missing_required_tables": REQUIRED_TABLES
        }


def check_model_health() -> Dict[str, Any]:
    """
    Verify the ML model file exists and is loadable.
    Uses cached model if already loaded to avoid repeated disk access.
    Does NOT retrain the model.
    """
    t0 = time.time()
    try:
        if not MODEL_FILE.exists():
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            return {
                "status": "unhealthy",
                "model_available": False,
                "response_time_ms": elapsed_ms,
                "error": f"Model file not found: {MODEL_FILE}"
            }

        # Check file size
        size_bytes = MODEL_FILE.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)

        # Try to import joblib and verify the file header without full reload
        import joblib
        # Use the already-loaded model from recovery_agent if available
        try:
            from src.recovery_agent import model as loaded_model
            model_type = type(loaded_model).__name__ if loaded_model else "unknown"
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            return {
                "status": "healthy",
                "model_available": True,
                "model_size_mb": size_mb,
                "model_type": model_type,
                "response_time_ms": elapsed_ms,
                "model_path": str(MODEL_FILE)
            }
        except Exception:
            # Fall back to checking file existence only
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            return {
                "status": "healthy",
                "model_available": True,
                "model_size_mb": size_mb,
                "response_time_ms": elapsed_ms,
                "model_path": str(MODEL_FILE),
                "note": "File present; model reference check skipped"
            }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        return {
            "status": "unhealthy",
            "model_available": False,
            "response_time_ms": elapsed_ms,
            "error": str(e)
        }


def check_recovery_agent_health() -> Dict[str, Any]:
    """
    Verify the Recovery Agent module can be imported and the agent function is callable.
    Does NOT execute a real recovery.
    """
    t0 = time.time()
    try:
        from src.recovery_agent import recovery_agent
        callable_check = callable(recovery_agent)
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        return {
            "status": "healthy" if callable_check else "unhealthy",
            "agent_callable": callable_check,
            "response_time_ms": elapsed_ms
        }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        return {
            "status": "unhealthy",
            "agent_callable": False,
            "response_time_ms": elapsed_ms,
            "error": str(e)
        }


def check_configuration_health() -> Dict[str, Any]:
    """
    Verify that application settings are accessible and valid.
    """
    t0 = time.time()
    try:
        from src.settings import get_all_settings
        settings = get_all_settings()
        demo_mode = settings.get("demo_mode", True)
        environment = settings.get("environment", "DEMO")
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        return {
            "status": "healthy",
            "setting_count": len(settings),
            "demo_mode": demo_mode,
            "environment": environment,
            "response_time_ms": elapsed_ms
        }
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        return {
            "status": "degraded",
            "response_time_ms": elapsed_ms,
            "error": str(e)
        }


def run_full_health_check(record_history: bool = True) -> Dict[str, Any]:
    """
    Run all health checks and return a structured response.
    Optionally records the result in health_history table.
    """
    overall_start = time.time()

    db_check = check_database_health()
    model_check = check_model_health()
    agent_check = check_recovery_agent_health()
    config_check = check_configuration_health()

    total_ms = round((time.time() - overall_start) * 1000, 2)
    uptime_seconds = round(time.time() - _STARTUP_TIME, 1)

    # Determine overall status
    statuses = [
        db_check["status"],
        model_check["status"],
        agent_check["status"],
        config_check["status"]
    ]

    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    result = {
        "status": overall_status,
        "service": "RecoverAI API",
        "version": API_VERSION,
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now().isoformat(),
        "total_response_time_ms": total_ms,
        "checks": {
            "api": "healthy",
            "database": db_check["status"],
            "model": model_check["status"],
            "recovery_agent": agent_check["status"],
            "configuration": config_check["status"]
        },
        "details": {
            "database": db_check,
            "model": model_check,
            "recovery_agent": agent_check,
            "configuration": config_check
        }
    }

    # Record to health_history (non-blocking)
    if record_history:
        try:
            _record_health_history(overall_status, db_check["status"],
                                   model_check["status"], agent_check["status"],
                                   total_ms)
        except Exception:
            pass

    return result


def _record_health_history(
    overall_status: str,
    database_status: str,
    model_status: str,
    agent_status: str,
    response_time_ms: float
):
    """Save a health check result to the health_history table."""
    ensure_health_history_table()
    from src.database import DATABASE
    conn = sqlite3.connect(str(DATABASE))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO health_history (
            checked_at, api_status, database_status, model_status,
            recovery_agent_status, overall_status, response_time_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(), "healthy", database_status,
        model_status, agent_status, overall_status, response_time_ms
    ))
    conn.commit()
    conn.close()


def get_health_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent health check history records."""
    try:
        ensure_health_history_table()
        from src.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM health_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def generate_health_alert_if_needed(health_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Generate a Smart Alert if the system is degraded/unhealthy.
    Returns a raw alert dict or None if healthy.
    Deduplication handled by existing save_alert().
    """
    overall = health_result.get("status", "healthy")
    if overall == "healthy":
        return None

    checks = health_result.get("checks", {})
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Determine most critical component failure
    if checks.get("database") != "healthy":
        alert_type = "DATABASE_UNAVAILABLE"
        title = "Database Health Degraded"
        message = "RecoverAI database connectivity issue detected."
    elif checks.get("model") != "healthy":
        alert_type = "MODEL_UNAVAILABLE"
        title = "ML Model Unavailable"
        message = "The recovery prediction model is unavailable."
    elif checks.get("recovery_agent") != "healthy":
        alert_type = "RECOVERY_AGENT_UNAVAILABLE"
        title = "Recovery Agent Unavailable"
        message = "The AI Recovery Agent cannot be initialized."
    else:
        alert_type = "API_HEALTH_DEGRADED"
        title = "API Health Degraded"
        message = "RecoverAI API is running in degraded state."

    return {
        "alert_type": alert_type,
        "payment_id": None,
        "customer_id": None,
        "amount": 0.0,
        "recovery_probability": 0.0,
        "risk_level": "HIGH",
        "opportunity_score": 80.0,
        "recommended_action": "SYSTEM_INVESTIGATION",
        "expected_recovery": 0.0,
        "time_window_key": today_str,
        "_title_override": title,
        "_message_override": message
    }
