"""
RecoverAI Application Settings Module
Persists configuration in the SQLite database (app_settings table).
Safe, validated settings only — no credentials, no secrets, no API keys.
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# Default Settings Registry
# ============================================================

DEFAULT_SETTINGS: Dict[str, Any] = {
    # General
    "app_name": "RecoverAI",
    "environment": "DEMO",
    "currency": "INR",
    "timezone": "Asia/Kolkata",
    "demo_mode": True,

    # Recovery Configuration
    "max_recovery_attempts": 3,
    "minimum_recovery_probability": 0.50,
    "high_risk_threshold": 0.30,
    "automatic_retry_enabled": False,
    "customer_action_threshold": 0.40,

    # Alert Configuration
    "smart_alerts_enabled": True,
    "critical_alerts_enabled": True,
    "high_revenue_risk_alerts_enabled": True,
    "recovery_failure_alerts_enabled": True,
    "prediction_mismatch_alerts_enabled": True,
    "dashboard_alerts_enabled": True,
    "email_notifications_enabled": False,

    # Dashboard Preferences
    "default_dashboard_page": "Dashboard",
    "rows_per_page": 25,
    "auto_refresh_enabled": False,
    "refresh_interval_seconds": 60,
    "chart_theme": "default",

    # Version info (read-only)
    "api_version": "3.0.0",
}

# ============================================================
# Validation Rules: (min, max) for numeric, or list of allowed for str
# ============================================================

SETTING_VALIDATORS: Dict[str, Any] = {
    "max_recovery_attempts": {"type": int, "min": 1, "max": 10},
    "minimum_recovery_probability": {"type": float, "min": 0.0, "max": 1.0},
    "high_risk_threshold": {"type": float, "min": 0.0, "max": 1.0},
    "customer_action_threshold": {"type": float, "min": 0.0, "max": 1.0},
    "rows_per_page": {"type": int, "min": 5, "max": 200},
    "refresh_interval_seconds": {"type": int, "min": 10, "max": 3600},
    "environment": {"type": str, "allowed": ["DEMO", "DEVELOPMENT", "STAGING", "PRODUCTION"]},
    "currency": {"type": str, "allowed": ["INR", "USD", "EUR", "GBP"]},
    "chart_theme": {"type": str, "allowed": ["default", "dark", "minimal"]},
}

# Read-only settings that cannot be changed via PUT
READ_ONLY_SETTINGS = {"api_version"}


def _get_db():
    """Import get_connection lazily to avoid circular imports."""
    from src.database import get_connection
    return get_connection()


def ensure_settings_table():
    """Create app_settings table if it doesn't exist."""
    from src.database import get_connection, DATA_DIR
    import sqlite3
    from src.database import DATABASE
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_settings_key ON app_settings (key)")
    conn.commit()
    conn.close()


def _serialize(value: Any) -> str:
    """Serialize a Python value to a JSON string for storage."""
    return json.dumps(value)


def _deserialize(raw: str) -> Any:
    """Deserialize a stored JSON string back to Python value."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def validate_setting(key: str, value: Any) -> Any:
    """
    Validate and coerce a setting value.
    Raises ValueError if invalid.
    Returns the coerced value.
    """
    if key in READ_ONLY_SETTINGS:
        raise ValueError(f"Setting '{key}' is read-only and cannot be changed.")

    if key not in DEFAULT_SETTINGS:
        raise ValueError(f"Unknown setting key '{key}'. Allowed keys: {sorted(DEFAULT_SETTINGS.keys())}")

    rules = SETTING_VALIDATORS.get(key)
    if rules is None:
        return value  # No specific validation, accept as-is

    # Coerce type
    try:
        coerced = rules["type"](value)
    except (TypeError, ValueError):
        raise ValueError(f"Setting '{key}' must be of type {rules['type'].__name__}.")

    # Range check
    if "min" in rules and coerced < rules["min"]:
        raise ValueError(f"Setting '{key}' must be >= {rules['min']}. Got: {coerced}")
    if "max" in rules and coerced > rules["max"]:
        raise ValueError(f"Setting '{key}' must be <= {rules['max']}. Got: {coerced}")

    # Allowed values check
    if "allowed" in rules and coerced not in rules["allowed"]:
        raise ValueError(f"Setting '{key}' must be one of {rules['allowed']}. Got: '{coerced}'")

    return coerced


def get_all_settings() -> Dict[str, Any]:
    """
    Return all settings, merging defaults with database overrides.
    Database values take precedence over defaults.
    """
    ensure_settings_table()
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM app_settings")
    rows = cursor.fetchall()
    conn.close()

    result = dict(DEFAULT_SETTINGS)
    for row in rows:
        key = row["key"]
        if key in DEFAULT_SETTINGS:
            result[key] = _deserialize(row["value"])
    return result


def get_setting(key: str) -> Any:
    """Get a single setting value (database override or default)."""
    all_settings = get_all_settings()
    if key not in all_settings:
        raise KeyError(f"Setting '{key}' not found.")
    return all_settings[key]


def set_setting(key: str, value: Any) -> Dict[str, Any]:
    """
    Persist a single setting to the database.
    Returns the updated setting dict.
    Raises ValueError for invalid values.
    """
    ensure_settings_table()
    coerced = validate_setting(key, value)
    now = datetime.now().isoformat()
    serialized = _serialize(coerced)

    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
    """, (key, serialized, now))
    conn.commit()
    conn.close()

    return {"key": key, "value": coerced, "updated_at": now}


def reset_settings() -> Dict[str, Any]:
    """
    Reset all settings to defaults by deleting all database overrides.
    Does NOT delete any other data — only the app_settings table rows.
    Returns the default settings dict.
    """
    ensure_settings_table()
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM app_settings")
    conn.commit()
    conn.close()
    return dict(DEFAULT_SETTINGS)


def get_settings_for_api() -> Dict[str, Any]:
    """
    Return settings safe for API exposure (no credentials, no internal-only keys).
    """
    all_s = get_all_settings()
    # Explicitly exclude any future sensitive keys
    safe_keys = {k for k in all_s if k not in {"api_version"}}
    return {k: all_s[k] for k in safe_keys}
