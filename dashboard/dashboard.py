import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import sys

# ==============================================================================
# Setup Paths & Import Engine
# ==============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.explanation_engine import (
    generate_decision_explanation,
    format_failure_reason,
    format_action_label
)

# ==============================================================================
# Streamlit Page Configuration
# ==============================================================================

st.set_page_config(
    page_title="RecoverAI — AI Payment Revenue Recovery Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# Modern Fintech CSS Design System
# ==============================================================================

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0F172A;
    }

    .main {
        background-color: #F8FAFC;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1440px;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem;
        padding-left: 1.2rem;
        padding-right: 1.2rem;
    }

    /* Brand Header */
    .brand-title {
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #0F172A;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .brand-subtitle {
        font-size: 0.875rem;
        color: #64748B;
        margin-top: 0.2rem;
        font-weight: 500;
    }

    /* Status Badges */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        background: #F1F5F9;
        color: #334155;
        border: 1px solid #E2E8F0;
    }
    .status-dot-green {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }
    .status-dot-red {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #EF4444;
        box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
    }

    /* Priority Badges */
    .prio-badge-critical {
        background-color: #FFE4E6;
        color: #BE123C;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        display: inline-block;
        border: 1px solid #FECDD3;
    }
    .prio-badge-high {
        background-color: #FEF3C7;
        color: #B45309;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        display: inline-block;
        border: 1px solid #FDE68A;
    }
    .prio-badge-medium {
        background-color: #EFF6FF;
        color: #1D4ED8;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        display: inline-block;
        border: 1px solid #BFDBFE;
    }
    .prio-badge-low {
        background-color: #F5F3FF;
        color: #6D28D9;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        display: inline-block;
        border: 1px solid #DDD6FE;
    }
    .prio-badge-very-low {
        background-color: #F1F5F9;
        color: #64748B;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        display: inline-block;
        border: 1px solid #E2E8F0;
    }

    /* Alert Lifecycle Status Badges */
    .alert-status-open {
        background-color: #FEF2F2;
        color: #991B1B;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        border: 1px solid #FECACA;
    }
    .alert-status-ack {
        background-color: #FFFBEB;
        color: #92400E;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        border: 1px solid #FDE68A;
    }
    .alert-status-res {
        background-color: #ECFDF5;
        color: #065F46;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        border: 1px solid #A7F3D0;
    }

    /* Alert Feed Card */
    .smart-alert-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.25rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(15, 23, 42, 0.02);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .smart-alert-card:hover {
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
    }
    .smart-alert-crit {
        border-left: 5px solid #E11D48;
    }
    .smart-alert-high {
        border-left: 5px solid #D97706;
    }
    .smart-alert-med {
        border-left: 5px solid #2563EB;
    }
    .smart-alert-low {
        border-left: 5px solid #64748B;
    }

    /* KPI Hero Cards */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem 1.3rem;
        box-shadow: 0 2px 4px rgba(15, 23, 42, 0.02);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
    }
    .kpi-label {
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        margin-bottom: 0.4rem;
    }
    .kpi-value {
        font-size: 1.7rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #0F172A;
        line-height: 1.2;
    }
    .kpi-subtext {
        font-size: 0.75rem;
        color: #64748B;
        font-weight: 500;
        margin-top: 0.35rem;
    }

    /* Top Opportunity Hero Banner */
    .top-opp-banner {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 1.5rem 1.75rem;
        color: #FFFFFF;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.1);
        margin-bottom: 1.25rem;
    }
    .top-opp-tag {
        background: rgba(225, 29, 72, 0.2);
        color: #FDA4AF;
        border: 1px solid rgba(244, 63, 94, 0.4);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* Opportunity Card */
    .opp-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        box-shadow: 0 2px 4px rgba(15, 23, 42, 0.02);
        border-top: 3px solid #2563EB;
        height: 100%;
    }
    .opp-rank {
        font-size: 0.75rem;
        font-weight: 800;
        color: #2563EB;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .opp-val {
        font-size: 1.2rem;
        font-weight: 800;
        color: #0F172A;
    }
    .opp-prob {
        font-size: 0.8rem;
        font-weight: 700;
        color: #059669;
    }

    /* Section Subheadings */
    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Explanation Styling */
    .explanation-narrative {
        background: #F8FAFC;
        border-left: 4px solid #2563EB;
        border-radius: 0 8px 8px 0;
        padding: 0.9rem 1.15rem;
        font-size: 0.9rem;
        line-height: 1.55;
        color: #1E293B;
        margin-bottom: 1rem;
    }
    .factor-badge-item {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 0.55rem 0.75rem;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        margin-bottom: 0.4rem;
        font-size: 0.825rem;
        color: #334155;
    }
    .factor-check {
        color: #10B981;
        font-weight: 800;
        font-size: 0.95rem;
    }
    .math-callout {
        background: #F1F5F9;
        border: 1px dashed #CBD5E1;
        border-radius: 6px;
        padding: 0.65rem 0.85rem;
        font-family: 'Inter', monospace;
        font-size: 0.9rem;
        font-weight: 700;
        color: #0F172A;
        display: inline-block;
    }
    .next-step-box {
        background: #FAF5FF;
        border: 1px solid #E9D5FF;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        color: #6B21A8;
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* AI Status in Sidebar */
    .ai-status-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border-radius: 10px;
        padding: 1rem;
        color: #FFFFFF;
        margin-top: 1rem;
        border: 1px solid #334155;
    }

    .stButton > button {
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==============================================================================
# API Client & Backend Communication (Pure HTTP - No Direct SQLite)
# ==============================================================================

API_BASE_URL = "http://127.0.0.1:8000"


def check_backend_health(api_url: str = API_BASE_URL) -> dict:
    """Check FastAPI server status."""
    try:
        res = requests.get(f"{api_url}/", timeout=2.0)
        if res.status_code == 200:
            return {"api_online": True, "model_active": True, "db_connected": True}
    except Exception:
        pass
    return {"api_online": False, "model_active": False, "db_connected": False}


def fetch_decisions(api_url: str = API_BASE_URL) -> tuple[pd.DataFrame, bool, str]:
    """Fetch recovery decision history directly from FastAPI GET /decisions."""
    try:
        res = requests.get(f"{api_url}/decisions", timeout=3.5)
        if res.status_code == 200:
            data = res.json()
            decisions = data.get("decisions", [])
            if decisions:
                df = pd.DataFrame(decisions)
                return df, True, ""
            return pd.DataFrame(), True, ""
        return pd.DataFrame(), False, f"API returned HTTP {res.status_code}"
    except requests.exceptions.ConnectionError:
        return pd.DataFrame(), False, "Connection refused. FastAPI backend is offline."
    except Exception as e:
        return pd.DataFrame(), False, str(e)


def fetch_revenue_opportunities(
    params: dict = None,
    api_url: str = API_BASE_URL
) -> tuple[pd.DataFrame, bool, str]:
    """Fetch ranked revenue recovery opportunities from FastAPI GET /revenue-opportunities."""
    try:
        res = requests.get(f"{api_url}/revenue-opportunities", params=params, timeout=3.5)
        if res.status_code == 200:
            data = res.json()
            opps = data.get("opportunities", [])
            if opps:
                df = pd.DataFrame(opps)
                return df, True, ""
            return pd.DataFrame(), True, ""
        return pd.DataFrame(), False, f"API returned HTTP {res.status_code}"
    except requests.exceptions.ConnectionError:
        return pd.DataFrame(), False, "Connection refused. FastAPI backend is offline."
    except Exception as e:
        return pd.DataFrame(), False, str(e)


def fetch_alerts(params: dict = None, api_url: str = API_BASE_URL) -> tuple[pd.DataFrame, bool, str]:
    """Fetch Smart Alerts from FastAPI GET /alerts."""
    try:
        res = requests.get(f"{api_url}/alerts", params=params, timeout=3.5)
        if res.status_code == 200:
            alerts = res.json()
            if alerts:
                df = pd.DataFrame(alerts)
                return df, True, ""
            return pd.DataFrame(), True, ""
        return pd.DataFrame(), False, f"API returned HTTP {res.status_code}"
    except requests.exceptions.ConnectionError:
        return pd.DataFrame(), False, "Connection refused. FastAPI backend is offline."
    except Exception as e:
        return pd.DataFrame(), False, str(e)


def fetch_alerts_summary(api_url: str = API_BASE_URL) -> tuple[dict, bool, str]:
    """Fetch Smart Alerts summary and financial impact metrics from FastAPI GET /alerts/summary."""
    try:
        res = requests.get(f"{api_url}/alerts/summary", timeout=3.5)
        if res.status_code == 200:
            return res.json(), True, ""
        return {}, False, f"API returned HTTP {res.status_code}"
    except requests.exceptions.ConnectionError:
        return {}, False, "Connection refused. FastAPI backend is offline."
    except Exception as e:
        return {}, False, str(e)


def acknowledge_alert_api(alert_id: str, api_url: str = API_BASE_URL) -> tuple[bool, str]:
    """Acknowledge an alert via FastAPI POST /alerts/{alert_id}/acknowledge."""
    try:
        res = requests.post(f"{api_url}/alerts/{alert_id}/acknowledge", timeout=3.5)
        if res.status_code == 200:
            return True, "Alert acknowledged successfully."
        err_msg = res.json().get("detail", res.text)
        return False, err_msg
    except Exception as e:
        return False, str(e)


def resolve_alert_api(alert_id: str, api_url: str = API_BASE_URL) -> tuple[bool, str]:
    """Resolve an alert via FastAPI POST /alerts/{alert_id}/resolve."""
    try:
        res = requests.post(f"{api_url}/alerts/{alert_id}/resolve", timeout=3.5)
        if res.status_code == 200:
            return True, "Alert marked as RESOLVED."
        err_msg = res.json().get("detail", res.text)
        return False, err_msg
    except Exception as e:
        return False, str(e)


def run_recovery_simulation_api(payload: dict, api_url: str = API_BASE_URL) -> tuple[dict, bool, str]:
    """Execute what-if recovery simulation via FastAPI POST /simulate-recovery."""
    try:
        res = requests.post(f"{api_url}/simulate-recovery", json=payload, timeout=4.5)
        if res.status_code == 200:
            return res.json(), True, ""
        err_msg = res.json().get("detail", res.text)
        return {}, False, err_msg
    except requests.exceptions.ConnectionError:
        return {}, False, "Connection refused. FastAPI backend is offline."
    except Exception as e:
        return {}, False, str(e)


def fetch_simulations(limit: int = 50, api_url: str = API_BASE_URL) -> tuple[pd.DataFrame, bool, str]:
    """Fetch recent simulation history runs from FastAPI GET /simulations."""
    try:
        res = requests.get(f"{api_url}/simulations", params={"limit": limit}, timeout=3.5)
        if res.status_code == 200:
            data = res.json()
            sims = data.get("simulations", [])
            if sims:
                return pd.DataFrame(sims), True, ""
            return pd.DataFrame(), True, ""
        return pd.DataFrame(), False, f"API returned HTTP {res.status_code}"
    except requests.exceptions.ConnectionError:
        return pd.DataFrame(), False, "Connection refused. FastAPI backend is offline."
    except Exception as e:
        return pd.DataFrame(), False, str(e)


# ==============================================================================
# Helper Formats & Badges
# ==============================================================================

def format_priority_badge(priority: str) -> str:
    p = str(priority).upper()
    if p == "CRITICAL":
        return '<span class="prio-badge-critical">🔴 CRITICAL</span>'
    elif p == "HIGH":
        return '<span class="prio-badge-high">🟠 HIGH</span>'
    elif p == "MEDIUM":
        return '<span class="prio-badge-medium">🟡 MEDIUM</span>'
    elif p == "LOW":
        return '<span class="prio-badge-low">🟣 LOW</span>'
    else:
        return '<span class="prio-badge-very-low">⚪ VERY LOW</span>'


def format_alert_status_badge(status: str) -> str:
    s = str(status).upper()
    if s == "OPEN":
        return '<span class="alert-status-open">● OPEN</span>'
    elif s == "ACKNOWLEDGED":
        return '<span class="alert-status-ack">◐ ACKNOWLEDGED</span>'
    else:
        return '<span class="alert-status-res">✔ RESOLVED</span>'


def format_risk_badge(risk: str) -> str:
    r = str(risk).upper()
    if r == "LOW":
        return "🟢 LOW"
    elif r == "MEDIUM":
        return "🟡 MEDIUM"
    return "🔴 HIGH"


# ==============================================================================
# Calculation Helpers
# ==============================================================================

def calculate_kpis(df: pd.DataFrame) -> dict:
    """Compute real KPI metrics strictly from the API data."""
    if df.empty:
        return {
            "payments_analyzed": 0,
            "revenue_at_risk": 0.0,
            "expected_recovery": 0.0,
            "recovery_potential": 0.0,
            "avg_probability": 0.0,
            "low_risk": 0,
            "med_risk": 0,
            "high_risk": 0,
            "low_pct": 0.0,
            "med_pct": 0.0,
            "high_pct": 0.0,
            "action_required_count": 0
        }

    total = len(df)
    at_risk = float(df["payment_amount"].sum()) if "payment_amount" in df.columns else 0.0
    expected = float(df["expected_revenue"].sum()) if "expected_revenue" in df.columns else 0.0
    rec_pot = (expected / at_risk * 100) if at_risk > 0 else 0.0
    avg_prob = float(df["recovery_probability"].mean() * 100) if "recovery_probability" in df.columns else 0.0

    low = int((df["risk_level"] == "LOW").sum()) if "risk_level" in df.columns else 0
    med = int((df["risk_level"] == "MEDIUM").sum()) if "risk_level" in df.columns else 0
    high = int((df["risk_level"] == "HIGH").sum()) if "risk_level" in df.columns else 0

    action_required = int((df["recommended_action"] != "STOP_AUTOMATIC_RECOVERY").sum()) if "recommended_action" in df.columns else 0

    return {
        "payments_analyzed": total,
        "revenue_at_risk": at_risk,
        "expected_recovery": expected,
        "recovery_potential": rec_pot,
        "avg_probability": avg_prob,
        "low_risk": low,
        "med_risk": med,
        "high_risk": high,
        "low_pct": (low / total * 100) if total > 0 else 0.0,
        "med_pct": (med / total * 100) if total > 0 else 0.0,
        "high_pct": (high / total * 100) if total > 0 else 0.0,
        "action_required_count": action_required
    }


def calculate_opportunity_kpis(df: pd.DataFrame) -> dict:
    """Compute KPI metrics specifically for Revenue Opportunities."""
    if df.empty:
        return {
            "total_opps": 0,
            "critical_opps": 0,
            "high_opps": 0,
            "total_potential_revenue": 0.0,
            "top_opp_value": 0.0
        }

    total = len(df)
    crit = int((df["priority_level"] == "CRITICAL").sum()) if "priority_level" in df.columns else 0
    high = int((df["priority_level"] == "HIGH").sum()) if "priority_level" in df.columns else 0
    potential = float(df["expected_revenue"].sum()) if "expected_revenue" in df.columns else 0.0
    top_val = float(df["expected_revenue"].max()) if "expected_revenue" in df.columns else 0.0

    return {
        "total_opps": total,
        "critical_opps": crit,
        "high_opps": high,
        "total_potential_revenue": potential,
        "top_opp_value": top_val
    }


# ==============================================================================
# Sidebar Renderer
# ==============================================================================

def render_sidebar(health: dict, open_alerts_count: int = 0) -> str:
    """Render sidebar navigation with active alert counter badge."""
    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 1.25rem;">
                <div style="background: #2563EB; color: white; width: 34px; height: 34px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.1rem;">
                    ⚡
                </div>
                <div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; line-height: 1.1;">RecoverAI</div>
                    <div style="font-size: 0.72rem; font-weight: 600; color: #2563EB;">FINTECH INTELLIGENCE</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<div style='font-size: 0.7rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 0.4rem;'>Menu</div>", unsafe_allow_html=True)

        alert_label = f"🚨 Smart Alerts ({open_alerts_count})" if open_alerts_count > 0 else "🚨 Smart Alerts"

        nav = st.radio(
            "Navigation Menu",
            options=[
                "🏠 Dashboard",
                alert_label,
                "💎 Revenue Opportunities",
                "🎯 Recovery Simulator",
                "💳 Payment Operations",
                "📊 Revenue Analytics",
                "🤖 AI Decisions",
                "📄 Reports"
            ],
            index=0,
            label_visibility="collapsed"
        )

        st.markdown("---")

        status_text = "Connected" if health["api_online"] else "Offline"
        status_color = "#34D399" if health["api_online"] else "#F87171"
        st.markdown(
            f"""
            <div class="ai-status-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="font-size: 0.7rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">AI Engine</div>
                    <div style="color: {status_color}; font-size: 0.75rem; font-weight: 700;">● {status_text}</div>
                </div>
                <div style="font-size: 0.9rem; font-weight: 700; color: #FFFFFF;">Smart Recovery & Alerts</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 2px;">Real-Time Failure Interception</div>
                <div style="display: flex; justify-content: space-between; margin-top: 0.6rem; border-top: 1px solid #334155; padding-top: 0.5rem; font-size: 0.72rem;">
                    <span>Val Accuracy: <strong style="color: #38BDF8;">85.50%</strong></span>
                    <span>Active Alerts: <strong style="color: #F87171;">{open_alerts_count} Open</strong></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div style="margin-top: 1.5rem; padding: 0.6rem 0.8rem; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; font-size: 0.75rem;">
                <div style="font-weight: 700; color: #0F172A;">Razorpay Merchant Ops</div>
                <div style="color: #64748B;">Admin • Production</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Normalize navigation return string
        if "🚨 Smart Alerts" in nav:
            return "🚨 Smart Alerts"
        if "Recovery Simulator" in nav or "Live Simulator" in nav:
            return "🎯 Recovery Simulator"
        return nav


# ==============================================================================
# Header Renderer
# ==============================================================================

def render_top_header(title: str, subtitle: str, health: dict):
    """Render top header with real-time status pills and refresh control."""
    col1, col2 = st.columns([6, 4], vertical_alignment="center")

    with col1:
        st.markdown(
            f"""
            <div>
                <h1 class="brand-title">{title}</h1>
                <p class="brand-subtitle">{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        btn_col, stat_col = st.columns([1, 2.2], vertical_alignment="center")

        with btn_col:
            if st.button("🔄 Refresh", width="stretch", help="Reload data from FastAPI backend"):
                st.rerun()

        with stat_col:
            api_dot = "status-dot-green" if health["api_online"] else "status-dot-red"
            model_dot = "status-dot-green" if health["model_active"] else "status-dot-red"
            db_dot = "status-dot-green" if health["db_connected"] else "status-dot-red"

            st.markdown(
                f"""
                <div style="display: flex; gap: 6px; justify-content: flex-end; flex-wrap: wrap;">
                    <div class="status-pill"><span class="{api_dot}"></span> API Connected</div>
                    <div class="status-pill"><span class="{model_dot}"></span> Model Active</div>
                    <div class="status-pill"><span class="{db_dot}"></span> Database Connected</div>
                </div>
                """,
                unsafe_allow_html=True
            )


# ==============================================================================
# KPI Cards Renderer
# ==============================================================================

def render_kpi_cards(kpis: dict):
    """Render the 4 main KPI metric cards using real values."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #2563EB;">
                <div class="kpi-label">Payments Analyzed</div>
                <div class="kpi-value">{kpis['payments_analyzed']}</div>
                <div class="kpi-subtext">Total processed payment failures</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #DC2626;">
                <div class="kpi-label">Revenue at Risk</div>
                <div class="kpi-value">₹{kpis['revenue_at_risk']:,.2f}</div>
                <div class="kpi-subtext">Failed transaction volume</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #059669;">
                <div class="kpi-label">Expected Recovery</div>
                <div class="kpi-value">₹{kpis['expected_recovery']:,.2f}</div>
                <div class="kpi-subtext">Predicted recoverable pool</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #8B5CF6;">
                <div class="kpi-label">Average Recovery Probability</div>
                <div class="kpi-value">{kpis['avg_probability']:.2f}%</div>
                <div class="kpi-subtext">Model confidence average</div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_payment_ops_kpis(kpis: dict):
    """Render KPI cards tailored specifically for Payment Operations."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #2563EB;">
                <div class="kpi-label">Total Payments</div>
                <div class="kpi-value">{kpis['payments_analyzed']}</div>
                <div class="kpi-subtext">Failed transactions in operations queue</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #D97706;">
                <div class="kpi-label">Payments Requiring Action</div>
                <div class="kpi-value">{kpis['action_required_count']}</div>
                <div class="kpi-subtext">Active recovery opportunities</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #DC2626;">
                <div class="kpi-label">High Risk Payments</div>
                <div class="kpi-value">{kpis['high_risk']}</div>
                <div class="kpi-subtext">{kpis['high_pct']:.1f}% of total failures</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #059669;">
                <div class="kpi-label">Expected Recovery</div>
                <div class="kpi-value">₹{kpis['expected_recovery']:,.2f}</div>
                <div class="kpi-subtext">Weighted revenue potential</div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_revenue_opportunity_kpis(kpis: dict):
    """Render 5 KPI Cards for the Revenue Opportunities feature."""
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #2563EB;">
                <div class="kpi-label">Total Opportunities</div>
                <div class="kpi-value">{kpis['total_opps']}</div>
                <div class="kpi-subtext">Ranked failed payments</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #E11D48;">
                <div class="kpi-label">Critical Priority</div>
                <div class="kpi-value">{kpis['critical_opps']}</div>
                <div class="kpi-subtext">Score &ge; 90.0 (Immediate)</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #D97706;">
                <div class="kpi-label">High Priority</div>
                <div class="kpi-value">{kpis['high_opps']}</div>
                <div class="kpi-subtext">Score 75.0 – 89.9</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #059669;">
                <div class="kpi-label">Potential Revenue</div>
                <div class="kpi-value">₹{kpis['total_potential_revenue']:,.2f}</div>
                <div class="kpi-subtext">&sum; Expected recoverable pool</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c5:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #7C3AED;">
                <div class="kpi-label">Top Opportunity</div>
                <div class="kpi-value">₹{kpis['top_opp_value']:,.2f}</div>
                <div class="kpi-subtext">Single highest expected value</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ==============================================================================
# FEATURE: SMART ALERTS VIEW
# ==============================================================================

def render_smart_alerts_view(health: dict):
    """
    Dedicated, production-grade Smart Alerts View.
    Communicates strictly via FastAPI over HTTP.
    """
    render_top_header(
        title="🚨 Smart Alerts",
        subtitle="Real-time revenue risk detection, intelligent priority triaging, and actionable resolution workflows.",
        health=health
    )

    if not health["api_online"]:
        st.warning("⚠️ **FastAPI backend is offline.** Please start the backend on port 8000 using `uvicorn api.main:app --port 8000`.")
        return

    # 1. Fetch Summary Metrics
    summary, s_ok, s_err = fetch_alerts_summary()
    if not s_ok:
        st.error(f"❌ Failed to load alert summary: {s_err}")
        summary = {
            "total_alerts": 0, "critical_alerts": 0, "high_alerts": 0, "medium_alerts": 0, "low_alerts": 0,
            "open_alerts": 0, "acknowledged_alerts": 0, "resolved_alerts": 0,
            "revenue_at_risk": 0.0, "potential_recovery": 0.0, "critical_revenue_at_risk": 0.0
        }

    # 2. Top KPI Cards (Alert Counts)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #EF4444;">
                <div class="kpi-label">🚨 Open Alerts</div>
                <div class="kpi-value">{summary.get('open_alerts', 0)}</div>
                <div class="kpi-subtext">{summary.get('acknowledged_alerts', 0)} Acknowledged &bull; {summary.get('resolved_alerts', 0)} Resolved</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with k2:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #BE123C;">
                <div class="kpi-label">🔴 Critical Priority</div>
                <div class="kpi-value">{summary.get('critical_alerts', 0)}</div>
                <div class="kpi-subtext">Immediate revenue threats</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with k3:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #D97706;">
                <div class="kpi-label">🟠 High Priority</div>
                <div class="kpi-value">{summary.get('high_alerts', 0)}</div>
                <div class="kpi-subtext">Action required</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with k4:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #2563EB;">
                <div class="kpi-label">🟡 Medium Priority</div>
                <div class="kpi-value">{summary.get('medium_alerts', 0)}</div>
                <div class="kpi-subtext">Scheduled & low friction</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 3. Revenue Impact Summary Cards
    st.markdown("<div class=\"section-title\">💰 Smart Alerts Financial Impact Summary</div>", unsafe_allow_html=True)
    with st.container(border=True):
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown(
                f"""
                <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 1rem;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #991B1B; text-transform: uppercase;">Revenue at Risk (Active Alerts)</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #991B1B; margin: 4px 0;">₹{summary.get('revenue_at_risk', 0.0):,.2f}</div>
                    <div style="font-size: 0.75rem; color: #B91C1C;">Total failed volume in OPEN & ACK alerts</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with r2:
            st.markdown(
                f"""
                <div style="background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 1rem;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #065F46; text-transform: uppercase;">Potential Recoverable Pool</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #065F46; margin: 4px 0;">₹{summary.get('potential_recovery', 0.0):,.2f}</div>
                    <div style="font-size: 0.75rem; color: #047857;">&sum; Expected recoverable value</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with r3:
            st.markdown(
                f"""
                <div style="background: #FFF1F2; border: 1px solid #FECDD3; border-radius: 8px; padding: 1rem;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #BE123C; text-transform: uppercase;">Critical Revenue at Risk</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: #BE123C; margin: 4px 0;">₹{summary.get('critical_revenue_at_risk', 0.0):,.2f}</div>
                    <div style="font-size: 0.75rem; color: #E11D48;">High-ticket CRITICAL threats</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 4. Multi-Filter Bar
    with st.container(border=True):
        st.markdown("<div style='font-size: 0.8rem; font-weight: 700; color: #64748B; text-transform: uppercase;'>Alert Filters</div>", unsafe_allow_html=True)
        af1, af2, af3 = st.columns(3)

        with af1:
            f_status = st.selectbox("Status", options=["All", "OPEN", "ACKNOWLEDGED", "RESOLVED"], index=0, key="al_status")
        with af2:
            f_prio = st.selectbox("Priority", options=["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"], index=0, key="al_prio")
        with af3:
            type_options = [
                "All",
                "HIGH_REVENUE_RISK",
                "CRITICAL_OPPORTUNITY",
                "HIGH_VALUE_RECOVERY",
                "LOW_RECOVERY_PROBABILITY",
                "CUSTOMER_ACTION_REQUIRED",
                "RETRY_RECOMMENDED",
                "REVENUE_SPIKE_RISK",
                "RECOVERY_PERFORMANCE_DROP"
            ]
            f_type = st.selectbox("Alert Type", options=type_options, format_func=lambda x: x.replace("_", " ").title() if x != "All" else "All", index=0, key="al_type")

    # Fetch alerts with filters
    q_params = {}
    if f_status != "All":
        q_params["status"] = f_status
    if f_prio != "All":
        q_params["priority"] = f_prio
    if f_type != "All":
        q_params["alert_type"] = f_type

    df_alerts, a_ok, a_err = fetch_alerts(params=q_params)

    if not a_ok:
        st.error(f"❌ Could not load alerts: {a_err}")
        return

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 5. Active Smart Alert Feed
    st.markdown(f"<div class=\"section-title\">⚡ Active Smart Alert Feed ({len(df_alerts)} Matched)</div>", unsafe_allow_html=True)

    if df_alerts.empty:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 2rem; text-align: center;">
                <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">🎉</div>
                <h4 style="color: #0F172A; font-weight: 700; margin-bottom: 0.25rem;">No Matching Alerts Found</h4>
                <p style="color: #64748B; font-size: 0.85rem;">All monitored conditions are currently within normal thresholds or resolved.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        for _, alert in df_alerts.iterrows():
            aid = alert["alert_id"]
            prio = alert["priority"]
            status_val = alert["status"]
            border_cls = (
                "smart-alert-crit" if prio == "CRITICAL" else (
                    "smart-alert-high" if prio == "HIGH" else (
                        "smart-alert-med" if prio == "MEDIUM" else "smart-alert-low"
                    )
                )
            )

            with st.container():
                st.markdown(
                    f"""
                    <div class="smart-alert-card {border_cls}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem; flex-wrap: wrap; gap: 6px;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                {format_priority_badge(prio)}
                                <strong style="font-size: 1.05rem; color: #0F172A;">{alert['title']}</strong>
                                <span style="font-size: 0.75rem; color: #64748B;">({aid})</span>
                            </div>
                            <div>
                                {format_alert_status_badge(status_val)}
                            </div>
                        </div>
                        <div style="font-size: 0.9rem; color: #334155; margin-bottom: 0.75rem;">
                            {alert['message']}
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.5rem; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.6rem 0.8rem; font-size: 0.8rem; margin-bottom: 0.75rem;">
                            <div><strong>Payment ID:</strong> {alert.get('payment_id') or 'N/A (System)'}</div>
                            <div><strong>Amount:</strong> ₹{float(alert.get('amount', 0.0)):,.2f}</div>
                            <div><strong>Recovery Prob:</strong> {float(alert.get('recovery_probability', 0.0)) * 100:.1f}%</div>
                            <div><strong>Opp Score:</strong> {float(alert.get('opportunity_score', 0.0)):.1f}</div>
                            <div><strong>Expected Recovery:</strong> ₹{float(alert.get('expected_recovery', 0.0)):,.2f}</div>
                            <div><strong>Action:</strong> {format_action_label(str(alert.get('recommended_action', '')))}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Interactive Action Bar & Explainability
                act_col1, act_col2, exp_col = st.columns([1, 1, 4])

                with act_col1:
                    if status_val == "OPEN":
                        if st.button(f"✅ Acknowledge", key=f"ack_{aid}", use_container_width=True):
                            ok, msg = acknowledge_alert_api(aid)
                            if ok:
                                st.success(f"Alert {aid} acknowledged.")
                                st.rerun()
                            else:
                                st.error(msg)
                    elif status_val == "ACKNOWLEDGED":
                        st.caption("◐ Acknowledged")

                with act_col2:
                    if status_val in ("OPEN", "ACKNOWLEDGED"):
                        if st.button(f"✨ Resolve", key=f"res_{aid}", use_container_width=True, type="primary"):
                            ok, msg = resolve_alert_api(aid)
                            if ok:
                                st.success(f"Alert {aid} resolved.")
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.caption("✔ Resolved")

                with exp_col:
                    with st.expander(f"🔍 Explainability & Next Steps for {aid}"):
                        st.markdown(f"**Trigger Reason:**\n```\n{alert.get('why_explanation', 'N/A')}\n```")
                        st.markdown(
                            f"""
                            <div class="next-step-box">
                                <span>📌</span>
                                <div><strong>Recommended Action:</strong> {alert.get('recommended_step', 'Inspect transaction.')}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 6. Alert History & Audit Table
    st.markdown("<div class=\"section-title\">📜 Smart Alert Audit History</div>", unsafe_allow_html=True)
    with st.container(border=True):
        if not df_alerts.empty:
            hist_df = df_alerts.copy()
            hist_df["Formatted Amount"] = hist_df["amount"].apply(lambda x: f"₹{x:,.2f}")
            hist_df["Expected Recovery"] = hist_df["expected_recovery"].apply(lambda x: f"₹{x:,.2f}")
            hist_df["Created At"] = pd.to_datetime(hist_df["created_at"]).dt.strftime("%d %b %Y, %H:%M")
            hist_df["Type"] = hist_df["alert_type"].apply(lambda x: x.replace("_", " ").title())
            hist_df["Payment"] = hist_df["payment_id"].fillna("System Metric")

            st.dataframe(
                hist_df[[
                    "alert_id",
                    "Type",
                    "priority",
                    "Payment",
                    "Formatted Amount",
                    "Expected Recovery",
                    "status",
                    "Created At"
                ]].rename(columns={
                    "alert_id": "Alert ID",
                    "priority": "Priority",
                    "status": "Status",
                    "Formatted Amount": "Amount"
                }),
                width="stretch",
                hide_index=True
            )

            # CSV Download Button
            csv_bytes = df_alerts.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Smart Alert Audit Log (.csv)",
                data=csv_bytes,
                file_name=f"recoverai_smart_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No alert history records found.")


def render_home_smart_alerts_section(health: dict, alert_summary: dict):
    """
    Renders the 🚨 SMART ALERTS section at the top of the main Dashboard.
    Displays KPI summary cards and active open alerts feed with actions.
    """
    st.markdown("<div class=\"section-title\" style=\"font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 0.5rem;\">🚨 SMART ALERTS</div>", unsafe_allow_html=True)
    
    # 1. Alert KPI Summary Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #EF4444;">
                <div class="kpi-label">🚨 Open Alerts</div>
                <div class="kpi-value">{alert_summary.get('open_alerts', 0)}</div>
                <div class="kpi-subtext">{alert_summary.get('acknowledged_alerts', 0)} Acknowledged &bull; {alert_summary.get('resolved_alerts', 0)} Resolved</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with k2:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #BE123C;">
                <div class="kpi-label">🔴 Critical Priority</div>
                <div class="kpi-value">{alert_summary.get('critical_alerts', 0)}</div>
                <div class="kpi-subtext">Immediate revenue threats</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with k3:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #D97706;">
                <div class="kpi-label">🟠 High Priority</div>
                <div class="kpi-value">{alert_summary.get('high_alerts', 0)}</div>
                <div class="kpi-subtext">Action required</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with k4:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left: 4px solid #2563EB;">
                <div class="kpi-label">🟡 Medium Priority</div>
                <div class="kpi-value">{alert_summary.get('medium_alerts', 0)}</div>
                <div class="kpi-subtext">Scheduled & low friction</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 2. Fetch top open alerts feed
    df_open_alerts, ok, _ = fetch_alerts(params={"status": "OPEN", "limit": 4})
    if ok and not df_open_alerts.empty:
        for _, alert in df_open_alerts.iterrows():
            aid = alert["alert_id"]
            prio = alert["priority"]
            status_val = alert["status"]
            border_cls = (
                "smart-alert-crit" if prio == "CRITICAL" else (
                    "smart-alert-high" if prio == "HIGH" else (
                        "smart-alert-med" if prio == "MEDIUM" else "smart-alert-low"
                    )
                )
            )

            with st.container():
                st.markdown(
                    f"""
                    <div class="smart-alert-card {border_cls}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem; flex-wrap: wrap; gap: 6px;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                {format_priority_badge(prio)}
                                <strong style="font-size: 1.05rem; color: #0F172A;">{alert['title']}</strong>
                                <span style="font-size: 0.75rem; color: #64748B;">({aid})</span>
                            </div>
                            <div>
                                {format_alert_status_badge(status_val)}
                            </div>
                        </div>
                        <div style="font-size: 0.9rem; color: #334155; margin-bottom: 0.75rem;">
                            {alert['message']}
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.5rem; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.6rem 0.8rem; font-size: 0.8rem; margin-bottom: 0.75rem;">
                            <div><strong>Payment ID:</strong> {alert.get('payment_id') or 'N/A (System)'}</div>
                            <div><strong>Amount:</strong> ₹{float(alert.get('amount', 0.0)):,.2f}</div>
                            <div><strong>Recovery Prob:</strong> {float(alert.get('recovery_probability', 0.0)) * 100:.1f}%</div>
                            <div><strong>Opp Score:</strong> {float(alert.get('opportunity_score', 0.0)):.1f}</div>
                            <div><strong>Expected Recovery:</strong> ₹{float(alert.get('expected_recovery', 0.0)):,.2f}</div>
                            <div><strong>Action:</strong> {format_action_label(str(alert.get('recommended_action', '')))}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Action buttons & Explainability
                act_col1, act_col2, exp_col = st.columns([1, 1, 4])
                with act_col1:
                    if st.button("✅ Acknowledge", key=f"home_ack_{aid}", use_container_width=True):
                        ack_ok, ack_msg = acknowledge_alert_api(aid)
                        if ack_ok:
                            st.success(f"Alert {aid} acknowledged.")
                            st.rerun()
                        else:
                            st.error(ack_msg)

                with act_col2:
                    if st.button("✨ Resolve", key=f"home_res_{aid}", use_container_width=True, type="primary"):
                        res_ok, res_msg = resolve_alert_api(aid)
                        if res_ok:
                            st.success(f"Alert {aid} resolved.")
                            st.rerun()
                        else:
                            st.error(res_msg)

                with exp_col:
                    with st.expander(f"🔍 Explainability & Next Steps for {aid}"):
                        st.markdown(f"**Trigger Reason:**\n```\n{alert.get('why_explanation', 'N/A')}\n```")
                        st.markdown(
                            f"""
                            <div class="next-step-box">
                                <span>📌</span>
                                <div><strong>Recommended Action:</strong> {alert.get('recommended_step', 'Inspect transaction.')}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1.25rem; text-align: center; margin-bottom: 1rem;">
                <span style="font-size: 1.5rem;">🎉</span>
                <div style="font-weight: 700; color: #0F172A; font-size: 0.95rem; margin-top: 4px;">No Open Alerts</div>
                <div style="color: #64748B; font-size: 0.8rem;">All revenue recovery operations are healthy and within safe thresholds.</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ==============================================================================
# Existing Views: Top Opportunity Hero, Visual Analytics, Operations, etc.
# ==============================================================================

def render_top_opportunity_hero(df: pd.DataFrame):
    """Render a prominent hero banner for the Rank #1 highest revenue opportunity."""
    if df.empty:
        return

    top = df.sort_values(by="revenue_opportunity_score", ascending=False).iloc[0]

    prob_pct = top["recovery_probability"] * 100
    prio = str(top.get("priority_level", "HIGH")).upper()
    act = format_action_label(str(top.get("recommended_action", "RETRY_PAYMENT")))
    score = top.get("revenue_opportunity_score", 0.0)
    pid = top.get("payment_id", f"PAY{top.get('id', 1):05d}")
    cid = top.get("customer_id", "CUST0001")
    amt = float(top.get("payment_amount", 0.0))
    exp_rev = float(top.get("expected_revenue", 0.0))
    exp_text = top.get("explanation", "This payment combines high transaction value with a strong probability of successful recovery, making it the highest-priority revenue opportunity.")

    st.markdown(
        f"""
        <div class="top-opp-banner">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; flex-wrap: wrap; gap: 8px;">
                <div class="top-opp-tag">🔥 TOP REVENUE OPPORTUNITY &bull; RANK #1</div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <span style="font-size: 0.8rem; color: #94A3B8;">Priority:</span>
                    {format_priority_badge(prio)}
                    <span style="background: rgba(37, 99, 235, 0.3); border: 1px solid rgba(96, 165, 250, 0.4); color: #93C5FD; font-size: 0.75rem; font-weight: 700; padding: 3px 8px; border-radius: 6px;">
                        {act}
                    </span>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Payment & Customer</div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #FFFFFF;">{pid}</div>
                    <div style="font-size: 0.75rem; color: #CBD5E1;">{cid}</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Transaction Amount</div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #F8FAFC;">₹{amt:,.2f}</div>
                    <div style="font-size: 0.75rem; color: #CBD5E1;">Failure: {format_failure_reason(top.get('failure_reason', ''))}</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Recovery Probability</div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #34D399;">{prob_pct:.1f}%</div>
                    <div style="font-size: 0.75rem; color: #CBD5E1;">Model Confidence</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Expected Recovery</div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #38BDF8;">₹{exp_rev:,.2f}</div>
                    <div style="font-size: 0.75rem; color: #CBD5E1;">Amount &times; Probability</div>
                </div>
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Opportunity Score</div>
                    <div style="font-size: 1.35rem; font-weight: 800; color: #FBBF24;">{score:.1f} <span style="font-size: 0.8rem; color: #94A3B8;">/ 100</span></div>
                    <div style="font-size: 0.75rem; color: #CBD5E1;">Multi-Factor Index</div>
                </div>
            </div>
            <div style="font-size: 0.85rem; color: #E2E8F0; line-height: 1.5; background: rgba(0, 0, 0, 0.25); padding: 0.75rem 1rem; border-radius: 8px; border-left: 3px solid #38BDF8;">
                <strong>💡 Intelligent Recommendation:</strong> {exp_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_revenue_opportunities_charts(df: pd.DataFrame):
    """Render 5 interactive charts for revenue recovery opportunities."""
    if df.empty:
        return

    st.markdown("<div class=\"section-title\">📈 Visual Analytics & Distribution</div>", unsafe_allow_html=True)

    r1_col1, r1_col2 = st.columns([1.2, 1])

    with r1_col1:
        st.markdown("**💰 Potential Recoverable Revenue by Priority Tier**")
        with st.container(border=True):
            prio_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "VERY LOW"]
            rev_prio = df.groupby("priority_level")["expected_revenue"].sum().reindex(prio_order, fill_value=0.0).reset_index()
            rev_prio.columns = ["Priority", "Expected Revenue"]

            color_map = {
                "CRITICAL": "#E11D48",
                "HIGH": "#D97706",
                "MEDIUM": "#2563EB",
                "LOW": "#7C3AED",
                "VERY LOW": "#64748B"
            }

            fig_prio_rev = px.bar(
                rev_prio,
                x="Priority",
                y="Expected Revenue",
                text=[f"₹{v:,.0f}" if v > 0 else "" for v in rev_prio["Expected Revenue"]],
                color="Priority",
                color_discrete_map=color_map
            )
            fig_prio_rev.update_layout(
                showlegend=False,
                height=230,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title="Expected Revenue (₹)", showgrid=True, gridcolor="#F1F5F9"),
                xaxis=dict(title="")
            )
            fig_prio_rev.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(fig_prio_rev, width="stretch", config={"displayModeBar": False})

    with r1_col2:
        st.markdown("**🎯 Number of Opportunities by Priority**")
        with st.container(border=True):
            prio_counts = df["priority_level"].value_counts().reindex(prio_order, fill_value=0).reset_index()
            prio_counts.columns = ["Priority", "Count"]
            active_prio = prio_counts[prio_counts["Count"] > 0]

            if not active_prio.empty:
                fig_donut = go.Figure(data=[
                    go.Pie(
                        labels=active_prio["Priority"],
                        values=active_prio["Count"],
                        hole=0.65,
                        marker=dict(colors=[color_map.get(p, "#64748B") for p in active_prio["Priority"]], line=dict(color="#FFFFFF", width=2)),
                        textinfo="percent+label",
                        textfont=dict(size=10, family="Plus Jakarta Sans")
                    )
                ])
                fig_donut.update_layout(
                    showlegend=False,
                    height=230,
                    margin=dict(l=5, r=5, t=5, b=5),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    annotations=[
                        dict(
                            text=f"<b>{len(df)}</b><br><span style='font-size:10px; color:#64748B;'>Total Opps</span>",
                            x=0.5, y=0.5,
                            font=dict(size=14, family="Plus Jakarta Sans", color="#0F172A"),
                            showarrow=False
                        )
                    ]
                )
                st.plotly_chart(fig_donut, width="stretch", config={"displayModeBar": False})
            else:
                st.info("No opportunity data.")

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    r2_col1, r2_col2 = st.columns([1.2, 1])

    with r2_col1:
        st.markdown("**🔍 Expected Recoverable Revenue by Failure Reason**")
        with st.container(border=True):
            fail_rev = df.groupby("failure_reason")["expected_revenue"].sum().reset_index()
            fail_rev["clean_reason"] = fail_rev["failure_reason"].apply(format_failure_reason)
            fail_rev = fail_rev.sort_values(by="expected_revenue", ascending=False)

            fig_fail = px.bar(
                fail_rev,
                x="expected_revenue",
                y="clean_reason",
                orientation="h",
                text=[f"₹{v:,.0f}" for v in fail_rev["expected_revenue"]],
                color="clean_reason",
                color_discrete_sequence=["#2563EB", "#10B981", "#D97706", "#DC2626", "#8B5CF6", "#64748B"]
            )
            fig_fail.update_layout(
                showlegend=False,
                height=230,
                margin=dict(l=10, r=15, t=5, b=5),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="Expected Revenue (₹)", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title="", autorange="reversed")
            )
            fig_fail.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(fig_fail, width="stretch", config={"displayModeBar": False})

    with r2_col2:
        st.markdown("**🤖 Recovery Strategy & Action Distribution**")
        with st.container(border=True):
            act_counts = df["recommended_action"].value_counts().reset_index()
            act_counts.columns = ["action", "count"]
            act_counts["clean_action"] = act_counts["action"].apply(format_action_label)

            fig_act = px.pie(
                act_counts,
                names="clean_action",
                values="count",
                hole=0.6,
                color_discrete_sequence=["#2563EB", "#7C3AED", "#D97706", "#DC2626", "#64748B"]
            )
            fig_act.update_layout(
                showlegend=True,
                legend=dict(orientation="h", y=-0.1, font=dict(size=10)),
                height=230,
                margin=dict(l=5, r=5, t=5, b=5),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_act, width="stretch", config={"displayModeBar": False})

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    st.markdown("**🎯 Opportunity Landscape: Recovery Probability vs Payment Amount**")
    with st.container(border=True):
        scatter_df = df.copy()
        scatter_df["Recovery %"] = (scatter_df["recovery_probability"] * 100).round(1)
        scatter_df["Formatted Amount"] = scatter_df["payment_amount"].apply(lambda x: f"₹{x:,.2f}")
        scatter_df["Formatted Expected"] = scatter_df["expected_revenue"].apply(lambda x: f"₹{x:,.2f}")
        scatter_df["Clean Failure"] = scatter_df["failure_reason"].apply(format_failure_reason)
        scatter_df["Clean Action"] = scatter_df["recommended_action"].apply(format_action_label)

        fig_scatter = px.scatter(
            scatter_df,
            x="payment_amount",
            y="Recovery %",
            size="expected_revenue",
            color="priority_level",
            hover_name="payment_id",
            hover_data={
                "payment_amount": False,
                "Recovery %": True,
                "Formatted Amount": True,
                "Formatted Expected": True,
                "Clean Failure": True,
                "Clean Action": True,
                "revenue_opportunity_score": True,
                "priority_level": False,
                "expected_revenue": False
            },
            color_discrete_map=color_map,
            size_max=22
        )
        fig_scatter.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="Payment Amount (₹)", showgrid=True, gridcolor="#F1F5F9"),
            yaxis=dict(title="Recovery Probability (%)", showgrid=True, gridcolor="#F1F5F9", range=[0, 105]),
            legend=dict(title="Priority Level", orientation="h", y=1.1, x=0)
        )
        st.plotly_chart(fig_scatter, width="stretch", config={"displayModeBar": False})


def render_revenue_opportunities_page(health: dict):
    """Dedicated Revenue Opportunities View."""
    render_top_header(
        title="💎 Revenue Opportunities",
        subtitle="Intelligent ranking of failed payments prioritized by recoverable revenue opportunity, ML probability, risk, and safety rules.",
        health=health
    )

    if not health["api_online"]:
        st.warning("⚠️ **FastAPI backend is offline.** Start the backend using `uvicorn api.main:app --port 8000`.")
        return

    # Filter Bar
    with st.container(border=True):
        st.markdown("<div style='font-size: 0.8rem; font-weight: 700; color: #64748B; text-transform: uppercase;'>Opportunity Filters & Sorting</div>", unsafe_allow_html=True)
        f1, f2, f3, f4, f5 = st.columns(5)

        with f1:
            sel_prio = st.selectbox("Priority Level", options=["All", "CRITICAL", "HIGH", "MEDIUM", "LOW", "VERY LOW"], index=0)
        with f2:
            sel_risk = st.selectbox("Risk Level", options=["All", "LOW", "MEDIUM", "HIGH"], index=0)
        with f3:
            all_reasons = ["All", "network_timeout", "technical_error", "insufficient_balance", "authentication_failed", "expired_card", "bank_decline"]
            sel_reason = st.selectbox("Failure Reason", options=all_reasons, format_func=lambda x: format_failure_reason(x) if x != "All" else "All", index=0)
        with f4:
            all_actions = ["All", "RETRY_PAYMENT", "SCHEDULE_RETRY", "SEND_PAYMENT_REMINDER", "CUSTOMER_ACTION_REQUIRED", "STOP_AUTOMATIC_RECOVERY"]
            sel_action = st.selectbox("Recommended Action", options=all_actions, format_func=lambda x: format_action_label(x) if x != "All" else "All", index=0)
        with f5:
            sort_options = {
                "Highest Opportunity": ("revenue_opportunity_score", "desc"),
                "Highest Expected Revenue": ("expected_revenue", "desc"),
                "Highest Payment Amount": ("payment_amount", "desc"),
                "Highest Recovery Probability": ("recovery_probability", "desc")
            }
            sel_sort_label = st.selectbox("Sort Opportunities By", options=list(sort_options.keys()), index=0)
            sort_field, sort_order = sort_options[sel_sort_label]

    query_params = {
        "sort_by": sort_field,
        "sort_order": sort_order
    }
    if sel_prio != "All":
        query_params["priority_level"] = sel_prio
    if sel_risk != "All":
        query_params["risk_level"] = sel_risk
    if sel_reason != "All":
        query_params["failure_reason"] = sel_reason
    if sel_action != "All":
        query_params["recommended_action"] = sel_action

    df_opps, success, err_msg = fetch_revenue_opportunities(params=query_params)

    if not success:
        st.error(f"❌ Failed to fetch revenue opportunities from API: {err_msg}")
        return

    if df_opps.empty:
        st.info("No opportunities match current filter criteria.")
        return

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    kpis = calculate_opportunity_kpis(df_opps)
    render_revenue_opportunity_kpis(kpis)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    render_top_opportunity_hero(df_opps)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    render_revenue_opportunities_charts(df_opps)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class=\"section-title\">📋 Revenue Opportunity Ranking Table</div>", unsafe_allow_html=True)
    with st.container(border=True):
        disp_table = df_opps.copy()
        disp_table["Rank"] = disp_table["priority_rank"].apply(lambda r: f"#{r}")
        disp_table["Amount"] = disp_table["payment_amount"].apply(lambda x: f"₹{x:,.2f}")
        disp_table["Expected Revenue"] = disp_table["expected_revenue"].apply(lambda x: f"₹{x:,.2f}")
        disp_table["Recovery %"] = (disp_table["recovery_probability"] * 100).apply(lambda x: f"{x:.1f}%")
        disp_table["Opportunity Score"] = disp_table["revenue_opportunity_score"].apply(lambda s: f"{s:.1f}")
        disp_table["Failure Reason"] = disp_table["failure_reason"].apply(format_failure_reason)
        disp_table["Recommended Action"] = disp_table["recommended_action"].apply(format_action_label)
        disp_table["Risk Level"] = disp_table["risk_level"].apply(format_risk_badge)

        table_cols = ["Rank", "payment_id", "customer_id", "Amount", "Recovery %", "Expected Revenue", "Opportunity Score", "priority_level", "Risk Level", "Recommended Action", "explanation"]
        disp_table = disp_table[table_cols].rename(columns={"payment_id": "Payment ID", "customer_id": "Customer ID", "priority_level": "Priority Tier", "explanation": "AI Opportunity Rationale"})

        st.dataframe(disp_table, width="stretch", hide_index=True)

        csv_bytes = df_opps.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Revenue Opportunities Report (.csv)", data=csv_bytes, file_name=f"recoverai_revenue_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="background: #FFF1F2; border: 1px solid #FECDD3; border-radius: 8px; padding: 0.85rem 1.15rem; font-size: 0.825rem; color: #9F1239;">
            <strong>🛡️ Safety Rule Supremacy Notice:</strong>
            RecoverAI strictly enforces compliance safety rules. Hard/permanent failure types (e.g. <em>Bank Decline</em>, <em>Expired Card</em>, <em>Authentication Failed</em>)
            are assigned <code>CUSTOMER_ACTION_REQUIRED</code> and will NEVER be automatically retried regardless of transaction value or opportunity score.
        </div>
        """,
        unsafe_allow_html=True
    )


def render_highest_recovery_opportunities(df: pd.DataFrame, max_items: int = 4):
    """Display top recovery opportunities sorted by expected_revenue DESC."""
    st.markdown("<div class=\"section-title\">🔥 Highest Recovery Opportunities</div>", unsafe_allow_html=True)

    if df.empty:
        st.info("No recovery opportunities available.")
        return

    top_df = df.sort_values(by="expected_revenue", ascending=False).head(max_items)
    cols = st.columns(len(top_df))

    for idx, (_, row) in enumerate(top_df.iterrows()):
        with cols[idx]:
            prob_pct = row["recovery_probability"] * 100
            st.markdown(
                f"""
                <div class="opp-card">
                    <div class="opp-rank">#{idx + 1} Priority Opportunity</div>
                    <div class="opp-val">₹{row['payment_amount']:,.2f}</div>
                    <div class="opp-prob">{prob_pct:.1f}% Recovery Probability</div>
                    <div style="font-size: 0.85rem; font-weight: 700; color: #0F172A; margin-top: 0.35rem;">
                        Expected: <span style="color: #059669;">₹{row['expected_revenue']:,.2f}</span>
                    </div>
                    <div style="font-size: 0.75rem; color: #64748B; margin-top: 0.25rem;">
                        {format_failure_reason(row['failure_reason'])} &bull; {format_action_label(row['recommended_action'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_ops_charts(df: pd.DataFrame, kpis: dict):
    """Render Risk Distribution and Failure Reason Analysis side by side."""
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("<div class=\"section-title\">🛡️ Risk Distribution</div>", unsafe_allow_html=True)
        with st.container(border=True):
            r_col1, r_col2 = st.columns([1.1, 1], vertical_alignment="center")

            labels = ["Low Risk", "Medium Risk", "High Risk"]
            values = [kpis["low_risk"], kpis["med_risk"], kpis["high_risk"]]
            colors = ["#10B981", "#F59E0B", "#EF4444"]

            f_labels, f_values, f_colors = [], [], []
            for l, v, c in zip(labels, values, colors):
                if v > 0:
                    f_labels.append(l)
                    f_values.append(v)
                    f_colors.append(c)

            if not f_values:
                f_labels, f_values, f_colors = ["No Data"], [1], ["#E2E8F0"]

            fig_risk = go.Figure(data=[
                go.Pie(
                    labels=f_labels,
                    values=f_values,
                    hole=0.65,
                    marker=dict(colors=f_colors, line=dict(color="#FFFFFF", width=2)),
                    textinfo="percent",
                    hoverinfo="label+value",
                    textfont=dict(size=11, family="Plus Jakarta Sans", color="#FFFFFF")
                )
            ])
            fig_risk.update_layout(
                showlegend=False,
                margin=dict(l=5, r=5, t=5, b=5),
                height=180,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                annotations=[
                    dict(
                        text=f"<b>{kpis['payments_analyzed']}</b><br><span style='font-size:10px; color:#64748B;'>Total</span>",
                        x=0.5, y=0.5,
                        font=dict(size=16, family="Plus Jakarta Sans", color="#0F172A"),
                        showarrow=False
                    )
                ]
            )

            with r_col1:
                st.plotly_chart(fig_risk, width="stretch", config={"displayModeBar": False})

            with r_col2:
                st.markdown(
                    f"""
                    <div style="display: flex; flex-direction: column; gap: 6px; font-size: 0.8rem;">
                        <div style="display: flex; justify-content: space-between; padding: 5px 8px; background: #ECFDF5; border-radius: 6px; color: #065F46; font-weight: 600;">
                            <span>🟢 Low Risk</span>
                            <span>{kpis['low_risk']} ({kpis['low_pct']:.1f}%)</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 5px 8px; background: #FFFBEB; border-radius: 6px; color: #92400E; font-weight: 600;">
                            <span>🟡 Med Risk</span>
                            <span>{kpis['med_risk']} ({kpis['med_pct']:.1f}%)</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 5px 8px; background: #FEF2F2; border-radius: 6px; color: #991B1B; font-weight: 600;">
                            <span>🔴 High Risk</span>
                            <span>{kpis['high_risk']} ({kpis['high_pct']:.1f}%)</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    with col2:
        st.markdown("<div class=\"section-title\">📊 Payments by Failure Reason</div>", unsafe_allow_html=True)
        with st.container(border=True):
            if not df.empty and "failure_reason" in df.columns:
                counts = df["failure_reason"].value_counts().reset_index()
                counts.columns = ["reason", "count"]
                counts["clean_reason"] = counts["reason"].apply(format_failure_reason)

                fig_f = px.bar(
                    counts,
                    x="count",
                    y="clean_reason",
                    orientation="h",
                    text="count",
                    color="clean_reason",
                    color_discrete_sequence=["#2563EB", "#7C3AED", "#D97706", "#DC2626", "#475569"]
                )
                fig_f.update_layout(
                    showlegend=False,
                    xaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Count"),
                    yaxis=dict(autorange="reversed", title=""),
                    margin=dict(l=10, r=15, t=5, b=5),
                    height=180,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Plus Jakarta Sans", size=11)
                )
                fig_f.update_traces(textposition="outside", cliponaxis=False)
                st.plotly_chart(fig_f, width="stretch", config={"displayModeBar": False})
            else:
                st.info("No failure breakdown available.")


def render_payment_ops_table(df: pd.DataFrame) -> pd.DataFrame:
    """Render the Payment Operations table with multi-criteria filters."""
    st.markdown("<div class=\"section-title\">📋 Payment Operations Decision Queue</div>", unsafe_allow_html=True)

    with st.container(border=True):
        if df.empty:
            st.info("No payment records found in database.")
            return df

        f1, f2, f3, f4 = st.columns(4)

        with f1:
            search_query = st.text_input("🔍 Search Payment ID / Keyword", placeholder="e.g. 5, timeout")
        with f2:
            risk_options = ["All", "LOW", "MEDIUM", "HIGH"]
            sel_risk = st.selectbox("Filter Risk Level", options=risk_options, index=0)
        with f3:
            all_reasons = ["All", "network_timeout", "technical_error", "insufficient_balance", "authentication_failed", "expired_card", "bank_decline"]
            sel_reason = st.selectbox("Filter Failure Reason", options=all_reasons, format_func=lambda x: format_failure_reason(x) if x != "All" else "All", index=0)
        with f4:
            all_actions = ["All", "RETRY_PAYMENT", "SCHEDULE_RETRY", "SEND_PAYMENT_REMINDER", "CUSTOMER_ACTION_REQUIRED", "STOP_AUTOMATIC_RECOVERY"]
            sel_action = st.selectbox("Filter Recommended Action", options=all_actions, format_func=lambda x: format_action_label(x) if x != "All" else "All", index=0)

        min_prob = st.slider("Minimum Recovery Probability (%)", min_value=0, max_value=100, value=0, step=5)

        filtered = df.copy()

        if search_query:
            q = search_query.strip().lower()
            filtered = filtered[
                filtered["id"].astype(str).str.contains(q) |
                filtered["failure_reason"].str.lower().str.contains(q) |
                filtered["reason"].str.lower().str.contains(q)
            ]

        if sel_risk != "All":
            filtered = filtered[filtered["risk_level"] == sel_risk]
        if sel_reason != "All":
            filtered = filtered[filtered["failure_reason"] == sel_reason]
        if sel_action != "All":
            filtered = filtered[filtered["recommended_action"] == sel_action]
        if "recovery_probability" in filtered.columns and min_prob > 0:
            filtered = filtered[(filtered["recovery_probability"] * 100) >= min_prob]

        display_df = filtered.copy()
        display_df["Amount"] = display_df["payment_amount"].apply(lambda x: f"₹{x:,.2f}")
        display_df["Expected Revenue"] = display_df["expected_revenue"].apply(lambda x: f"₹{x:,.2f}")
        display_df["Recovery %"] = (display_df["recovery_probability"] * 100).apply(lambda x: f"{x:.1f}%")
        display_df["Failure Reason"] = display_df["failure_reason"].apply(format_failure_reason)
        display_df["Recommended Action"] = display_df["recommended_action"].apply(format_action_label)
        display_df["Risk Level"] = display_df["risk_level"].apply(format_risk_badge)

        if "timestamp" in display_df.columns:
            display_df["Timestamp"] = pd.to_datetime(display_df["timestamp"]).dt.strftime("%d %b %Y, %H:%M")
        else:
            display_df["Timestamp"] = "-"

        display_df = display_df.rename(columns={"id": "Payment ID", "reason": "AI Decision Reason"})

        st.dataframe(
            display_df[[
                "Payment ID",
                "Amount",
                "Failure Reason",
                "Recovery %",
                "Expected Revenue",
                "Risk Level",
                "Recommended Action",
                "AI Decision Reason",
                "Timestamp"
            ]],
            width="stretch",
            hide_index=True
        )

        csv_bytes = filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Payment Operations Report (.csv)",
            data=csv_bytes,
            file_name=f"recoverai_payment_ops_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        return filtered


def render_decision_details_and_rules(df: pd.DataFrame):
    """Display the detailed AI Decision Explanation panel and decision rule matrix."""
    st.markdown("<div class=\"section-title\">🤖 AI Decision Explanation & Rule Matrix</div>", unsafe_allow_html=True)

    if df.empty:
        st.info("No payment selected.")
        return

    with st.container(border=True):
        decision_options = []
        for _, row in df.iterrows():
            lbl = f"Payment #{row['id']} — ₹{row['payment_amount']:,.2f} — {format_failure_reason(row['failure_reason'])} ({row['risk_level']} RISK)"
            decision_options.append((row['id'], lbl))

        labels = [opt[1] for opt in decision_options]
        sel_idx = st.selectbox("Select a payment to inspect AI decision", options=range(len(labels)), format_func=lambda i: labels[i], index=0)

        selected_id = decision_options[sel_idx][0]
        selected_row = df[df["id"] == selected_id].iloc[0].to_dict()

        exp = generate_decision_explanation(selected_row)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"**Payment Amount:** ₹{exp['payment_amount']:,.2f}")
            st.caption(f"Failure: {exp['formatted_reason']}")
        with m2:
            st.markdown(f"**Recovery Probability:** {exp['recovery_percentage']:.1f}%")
            st.caption("AI Model Score")
        with m3:
            st.markdown(f"**Risk Level:** {exp['risk_level']} RISK")
            st.caption("Safety Classification")
        with m4:
            st.markdown(f"**Recommended Action:** {exp['formatted_action']}")
            st.caption("Strategy Selected")

        st.markdown("---")

        st.markdown(
            f"""
            <div class="explanation-narrative">
                <strong>Decision Reason:</strong> {selected_row.get('reason', 'N/A')}<br>
                <span style="color: #64748B; font-size: 0.85rem; margin-top: 4px; display: inline-block;">
                    {exp['summary']}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_payment_operations_page(df: pd.DataFrame, health: dict):
    """Complete, dedicated Payment Operations Page."""
    render_top_header(
        title="💳 Payment Operations",
        subtitle="Monitor failed payments, AI recovery decisions, risk levels, and expected revenue opportunities.",
        health=health
    )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    kpis = calculate_kpis(df)
    render_payment_ops_kpis(kpis)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    render_highest_recovery_opportunities(df)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    render_ops_charts(df, kpis)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    filtered_df = render_payment_ops_table(df)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    render_decision_details_and_rules(filtered_df if not filtered_df.empty else df)


def render_revenue_analytics_page(df: pd.DataFrame, health: dict):
    """Complete, dedicated Revenue Analytics Page."""
    render_top_header(
        title="📊 Revenue Analytics",
        subtitle="AI-powered analysis of payment recovery opportunities and revenue at risk.",
        health=health
    )

    if df.empty:
        st.info("No revenue data available yet.")
        return

    kpis = calculate_kpis(df)
    render_kpi_cards(kpis)


# ==============================================================================
# FEATURE: RECOVERY SIMULATOR VIEW
# ==============================================================================

def render_recovery_simulator_page(health: dict):
    """
    Dedicated, production-grade What-If Recovery Simulator.
    Simulates recovery strategies, scenario comparisons, sensitivity analysis,
    and simulation audit history strictly via FastAPI over HTTP.
    """
    render_top_header(
        title="🎯 Recovery Simulator",
        subtitle="What-if recovery strategy modeling, scenario comparisons, revenue impact forecasting & multi-strategy optimization.",
        health=health
    )

    # Notice callout
    st.markdown(
        """
        <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-left: 5px solid #2563EB; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 0.85rem; color: #1E40AF; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.2rem;">💡</span>
            <div>
                <strong>Decision Support & Simulation Only:</strong>
                Simulate recovery strategies and estimate financial yield. No real payment gateway retries, customer SMS, or refunds are executed.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not health["api_online"]:
        st.warning("⚠️ **FastAPI backend is offline.** Please start the backend on port 8000 using `uvicorn api.main:app --port 8000`.")
        return

    sim_tab1, sim_tab2, sim_tab3, sim_tab4 = st.tabs([
        "🎯 Strategy Simulator",
        "⚔️ Scenario Comparison (A vs B)",
        "📈 Sensitivity & Failure Matrix",
        "📜 Simulation History"
    ])

    # --------------------------------------------------------------------------
    # TAB 1: 🎯 Strategy Simulator & Comparison
    # --------------------------------------------------------------------------
    with sim_tab1:
        st.markdown("<div class=\"section-title\">🛠️ Configure Payment Scenario & Strategy</div>", unsafe_allow_html=True)
        
        with st.container(border=True):
            col_in1, col_in2, col_in3 = st.columns([1.2, 1.2, 1.4])

            with col_in1:
                st.markdown("**💰 Transaction Details**")
                amt = st.number_input("Payment Amount (₹)", min_value=100.0, max_value=500000.0, value=10000.0, step=1000.0, key="sim_amt")
                pm = st.selectbox("Payment Method", options=["card", "upi", "netbanking", "wallet"], index=0, key="sim_pm")
                fr_options = [
                    "network_timeout",
                    "technical_error",
                    "insufficient_balance",
                    "authentication_failed",
                    "expired_card",
                    "bank_decline"
                ]
                fr = st.selectbox(
                    "Failure Reason",
                    options=fr_options,
                    format_func=lambda x: format_failure_reason(x),
                    index=0,
                    key="sim_fr"
                )

            with col_in2:
                st.markdown("**👤 Customer History**")
                pp = st.number_input("Previous Successful Payments", min_value=0, max_value=200, value=12, key="sim_pp")
                pf = st.number_input("Previous Failures", min_value=0, max_value=50, value=1, key="sim_pf")
                ds = st.number_input("Days Since Last Payment", min_value=0, max_value=365, value=3, key="sim_ds")
                sub = st.selectbox("Subscription Customer", options=[1, 0], format_func=lambda x: "Yes (Recurring)" if x == 1 else "No (One-time)", index=0, key="sim_sub")

            with col_in3:
                st.markdown("**⚡ Select Recovery Strategy**")
                strat_options = [
                    ("AUTOMATIC_RETRY", "⚡ Automatic Retry (Instant secondary switch)"),
                    ("CUSTOMER_ACTION", "👤 Customer Action (Send payment/2FA link)"),
                    ("PAYMENT_METHOD_CHANGE", "💳 Payment Method Change (Switch to UPI/Netbanking)"),
                    ("WAIT_AND_RETRY", "⏳ Wait & Retry (Scheduled off-peak retry)"),
                    ("NO_ACTION", "⛔ No Action (Abort recovery to save gateway fees)")
                ]
                strat_keys = [s[0] for s in strat_options]
                strat_labels = [s[1] for s in strat_options]
                sel_strat_idx = st.radio(
                    "Recovery Strategy",
                    options=range(len(strat_labels)),
                    format_func=lambda i: strat_labels[i],
                    index=0,
                    key="sim_strat_radio"
                )
                selected_strategy = strat_keys[sel_strat_idx]

                hr = st.slider("Transaction Hour", min_value=0, max_value=23, value=14, key="sim_hr")
                wk = st.selectbox("Day Type", options=[0, 1], format_func=lambda x: "Weekend" if x == 1 else "Weekday", index=0, key="sim_wk")

            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
            run_btn = st.button("🎯 Run Recovery Simulation", type="primary", use_container_width=True)

        # Simulation Execution (Auto-run or button click)
        payload = {
            "amount": float(amt),
            "payment_method": pm,
            "failure_reason": fr,
            "previous_payments": int(pp),
            "previous_failures": int(pf),
            "days_since_last_payment": int(ds),
            "subscription": int(sub),
            "hour": int(hr),
            "is_weekend": int(wk),
            "strategy": selected_strategy
        }

        if run_btn or "sim_result" not in st.session_state:
            sim_res, ok, err = run_recovery_simulation_api(payload)
            if ok:
                st.session_state["sim_result"] = sim_res
            else:
                st.error(f"❌ Simulation failed: {err}")
                sim_res = {}
        else:
            sim_res = st.session_state.get("sim_result", {})

        if sim_res:
            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            st.markdown("<div class=\"section-title\">🤖 AI Simulation Result & Projections</div>", unsafe_allow_html=True)

            # 1. KPI Result Cards
            k1, k2, k3, k4, k5 = st.columns(5)
            with k1:
                prob_val = sim_res.get("recovery_percentage", 0.0)
                st.markdown(
                    f"""
                    <div class="kpi-card" style="border-left: 4px solid #2563EB;">
                        <div class="kpi-label">Recovery Probability</div>
                        <div class="kpi-value" style="color: #2563EB;">{prob_val:.1f}%</div>
                        <div class="kpi-subtext">Estimated Strategy Yield</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with k2:
                exp_val = sim_res.get("expected_recovery", 0.0)
                st.markdown(
                    f"""
                    <div class="kpi-card" style="border-left: 4px solid #059669;">
                        <div class="kpi-label">Expected Recovery</div>
                        <div class="kpi-value" style="color: #059669;">₹{exp_val:,.2f}</div>
                        <div class="kpi-subtext">Projected Recoverable Pool</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with k3:
                risk_val = sim_res.get("risk_level", "MEDIUM")
                risk_color = "#10B981" if risk_val == "LOW" else ("#D97706" if risk_val == "MEDIUM" else "#DC2626")
                st.markdown(
                    f"""
                    <div class="kpi-card" style="border-left: 4px solid {risk_color};">
                        <div class="kpi-label">Risk Classification</div>
                        <div class="kpi-value" style="color: {risk_color};">{risk_val}</div>
                        <div class="kpi-subtext">Safety Rule Status</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with k4:
                opp_val = sim_res.get("opportunity_score", 0.0)
                st.markdown(
                    f"""
                    <div class="kpi-card" style="border-left: 4px solid #7C3AED;">
                        <div class="kpi-label">Opportunity Score</div>
                        <div class="kpi-value" style="color: #7C3AED;">{opp_val:.1f}</div>
                        <div class="kpi-subtext">Index Out of 100.0</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with k5:
                is_allowed = sim_res.get("strategy_allowed", True)
                status_txt = "ALLOWED" if is_allowed else "BLOCKED"
                status_bg = "#ECFDF5" if is_allowed else "#FEF2F2"
                status_fg = "#065F46" if is_allowed else "#991B1B"
                st.markdown(
                    f"""
                    <div class="kpi-card" style="border-left: 4px solid {status_fg}; background: {status_bg};">
                        <div class="kpi-label" style="color: {status_fg};">Strategy Status</div>
                        <div class="kpi-value" style="color: {status_fg}; font-size: 1.4rem;">{status_txt}</div>
                        <div class="kpi-subtext" style="color: {status_fg};">Recovery Agent Gate</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            # 2. 🏆 Best Strategy Banner
            best_strat_name = sim_res.get("best_strategy_display", "Automatic Retry")
            best_exp = sim_res.get("best_expected_recovery", 0.0)
            best_prob = sim_res.get("best_recovery_probability", 0.0) * 100
            st.markdown(
                f"""
                <div class="top-opp-banner" style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 8px;">
                        <div class="top-opp-tag">🏆 AI RECOMMENDED BEST STRATEGY</div>
                        <div style="font-size: 0.85rem; color: #94A3B8;">Optimal Risk-Weighted Revenue Yield</div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 0.75rem;">
                        <div>
                            <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Strategy</div>
                            <div style="font-size: 1.25rem; font-weight: 800; color: #FBBF24;">{best_strat_name}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Max Expected Recovery</div>
                            <div style="font-size: 1.25rem; font-weight: 800; color: #34D399;">₹{best_exp:,.2f}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Recovery Probability</div>
                            <div style="font-size: 1.25rem; font-weight: 800; color: #38BDF8;">{best_prob:.1f}%</div>
                        </div>
                    </div>
                    <div style="font-size: 0.85rem; color: #CBD5E1; background: rgba(0,0,0,0.3); padding: 0.6rem 0.85rem; border-radius: 6px; border-left: 3px solid #FBBF24;">
                        <strong>💡 Rationale:</strong> {sim_res.get('explanation', '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            # 3. 💰 Simulated Revenue Impact Cards
            st.markdown("<div class=\"section-title\">💰 Simulated Revenue Impact</div>", unsafe_allow_html=True)
            with st.container(border=True):
                r1, r2, r3, r4 = st.columns(4)
                with r1:
                    st.markdown(f"**Current Revenue At Risk:**<br><span style='font-size:1.3rem; font-weight:800; color:#DC2626;'>₹{sim_res.get('revenue_at_risk', 0.0):,.2f}</span>", unsafe_allow_html=True)
                with r2:
                    st.markdown(f"**Potential Recovery (Max):**<br><span style='font-size:1.3rem; font-weight:800; color:#059669;'>₹{sim_res.get('potential_recovery', 0.0):,.2f}</span>", unsafe_allow_html=True)
                with r3:
                    st.markdown(f"**Selected Strategy Recovery:**<br><span style='font-size:1.3rem; font-weight:800; color:#2563EB;'>₹{sim_res.get('expected_recovery', 0.0):,.2f}</span>", unsafe_allow_html=True)
                with r4:
                    st.markdown(f"**Potential Improvement:**<br><span style='font-size:1.3rem; font-weight:800; color:#7C3AED;'>+₹{sim_res.get('potential_improvement', 0.0):,.2f}</span>", unsafe_allow_html=True)

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            # 4. 📊 Strategy Comparison Matrix
            st.markdown("<div class=\"section-title\">📊 Compare All 5 Recovery Strategies</div>", unsafe_allow_html=True)
            comps = sim_res.get("strategy_comparisons", [])
            if comps:
                df_comp = pd.DataFrame(comps)
                
                # Chart
                c_fig = px.bar(
                    df_comp,
                    x="expected_recovery",
                    y="display_name",
                    orientation="h",
                    text=[f"₹{v:,.0f} ({p:.1f}%)" for v, p in zip(df_comp["expected_recovery"], df_comp["recovery_percentage"])],
                    color="risk_level",
                    color_discrete_map={"LOW": "#10B981", "MEDIUM": "#D97706", "HIGH": "#DC2626"},
                    title="Expected Recoverable Revenue by Strategy"
                )
                c_fig.update_layout(
                    height=240,
                    margin=dict(l=10, r=20, t=30, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(title="Expected Recoverable Revenue (₹)", showgrid=True, gridcolor="#F1F5F9"),
                    yaxis=dict(title="", autorange="reversed"),
                    legend=dict(title="Risk Level", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(c_fig, width="stretch", config={"displayModeBar": False})

                # Table
                disp_comp = df_comp.copy()
                disp_comp["Expected Recovery"] = disp_comp["expected_recovery"].apply(lambda x: f"₹{x:,.2f}")
                disp_comp["Recovery %"] = disp_comp["recovery_percentage"].apply(lambda x: f"{x:.1f}%")
                disp_comp["Allowed"] = disp_comp["strategy_allowed"].apply(lambda x: "✅ YES" if x else "⛔ NO (Blocked)")
                disp_comp["Risk"] = disp_comp["risk_level"].apply(format_risk_badge)
                
                st.dataframe(
                    disp_comp[[
                        "display_name",
                        "Recovery %",
                        "Expected Recovery",
                        "opportunity_score",
                        "Risk",
                        "Allowed",
                        "safety_note"
                    ]].rename(columns={
                        "display_name": "Strategy",
                        "opportunity_score": "Opp Score",
                        "safety_note": "Safety Note"
                    }),
                    width="stretch",
                    hide_index=True
                )

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            # 5. 🤖 AI Explanation & Key Factors
            with st.expander("🔍 Detailed AI Decision-Support Factors & Safety Matrix", expanded=True):
                st.markdown(f"**Simulation Narrative:**\n\n> {sim_res.get('explanation', '')}")
                kf = sim_res.get("key_factors", [])
                if kf:
                    st.markdown("**Key Influencing Factors:**")
                    st.dataframe(pd.DataFrame(kf), width="stretch", hide_index=True)

    # --------------------------------------------------------------------------
    # TAB 2: ⚔️ Scenario Comparison (Scenario A vs Scenario B)
    # --------------------------------------------------------------------------
    with sim_tab2:
        st.markdown("<div class=\"section-title\">⚔️ What-If Scenario Comparison (Scenario A vs Scenario B)</div>", unsafe_allow_html=True)
        st.caption("Compare how different transaction characteristics or recovery strategies impact revenue recovery odds.")

        sc_col1, sc_col2 = st.columns(2)

        with sc_col1:
            with st.container(border=True):
                st.markdown("<h4 style='color:#2563EB;'>🅰️ Scenario A</h4>", unsafe_allow_html=True)
                sa_amt = st.number_input("Amount (₹)", min_value=100.0, max_value=500000.0, value=10000.0, step=1000.0, key="sa_amt")
                sa_pm = st.selectbox("Method", options=["card", "upi", "netbanking", "wallet"], index=0, key="sa_pm")
                sa_fr = st.selectbox("Failure Reason", options=["network_timeout", "technical_error", "insufficient_balance", "authentication_failed", "expired_card", "bank_decline"], index=0, format_func=format_failure_reason, key="sa_fr")
                sa_st = st.selectbox("Strategy", options=["AUTOMATIC_RETRY", "CUSTOMER_ACTION", "PAYMENT_METHOD_CHANGE", "WAIT_AND_RETRY", "NO_ACTION"], index=0, format_func=lambda x: x.replace("_", " ").title(), key="sa_st")

        with sc_col2:
            with st.container(border=True):
                st.markdown("<h4 style='color:#7C3AED;'>🅱️ Scenario B</h4>", unsafe_allow_html=True)
                sb_amt = st.number_input("Amount (₹)", min_value=100.0, max_value=500000.0, value=10000.0, step=1000.0, key="sb_amt")
                sb_pm = st.selectbox("Method", options=["card", "upi", "netbanking", "wallet"], index=0, key="sb_pm")
                sb_fr = st.selectbox("Failure Reason", options=["network_timeout", "technical_error", "insufficient_balance", "authentication_failed", "expired_card", "bank_decline"], index=2, format_func=format_failure_reason, key="sb_fr")
                sb_st = st.selectbox("Strategy", options=["AUTOMATIC_RETRY", "CUSTOMER_ACTION", "PAYMENT_METHOD_CHANGE", "WAIT_AND_RETRY", "NO_ACTION"], index=1, format_func=lambda x: x.replace("_", " ").title(), key="sb_st")

        if st.button("⚔️ Compare Scenarios A & B", type="primary", use_container_width=True):
            p_a = {"amount": sa_amt, "payment_method": sa_pm, "failure_reason": sa_fr, "previous_payments": 10, "previous_failures": 1, "days_since_last_payment": 3, "subscription": 1, "strategy": sa_st}
            p_b = {"amount": sb_amt, "payment_method": sb_pm, "failure_reason": sb_fr, "previous_payments": 10, "previous_failures": 1, "days_since_last_payment": 3, "subscription": 1, "strategy": sb_st}

            res_a, ok_a, _ = run_recovery_simulation_api(p_a)
            res_b, ok_b, _ = run_recovery_simulation_api(p_b)

            if ok_a and ok_b:
                rev_a = res_a.get("expected_recovery", 0.0)
                rev_b = res_b.get("expected_recovery", 0.0)
                prob_a = res_a.get("recovery_percentage", 0.0)
                prob_b = res_b.get("recovery_percentage", 0.0)
                diff = rev_a - rev_b

                # Verdict Card
                if diff > 0:
                    v_color = "#059669"
                    v_text = f"🏆 **Scenario A Outperforms Scenario B** by **+₹{diff:,.2f}** in expected recovery ({prob_a - prob_b:+.1f}% probability)."
                elif diff < 0:
                    v_color = "#7C3AED"
                    v_text = f"🏆 **Scenario B Outperforms Scenario A** by **+₹{-diff:,.2f}** in expected recovery ({prob_b - prob_a:+.1f}% probability)."
                else:
                    v_color = "#2563EB"
                    v_text = "🤝 **Tie**: Both scenarios yield identical expected recovery outcomes."

                st.markdown(
                    f"""
                    <div style="background: #F8FAFC; border-left: 5px solid {v_color}; border-radius: 8px; padding: 1rem; margin-top: 1rem; margin-bottom: 1rem; font-size: 1.05rem;">
                        {v_text}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Comparison Metrics Table
                comp_rows = [
                    {"Metric": "Strategy", "Scenario A": res_a.get("strategy_display_name"), "Scenario B": res_b.get("strategy_display_name"), "Difference (A - B)": "-"},
                    {"Metric": "Recovery Probability", "Scenario A": f"{prob_a:.1f}%", "Scenario B": f"{prob_b:.1f}%", "Difference (A - B)": f"{prob_a - prob_b:+.1f}%"},
                    {"Metric": "Expected Recovery", "Scenario A": f"₹{rev_a:,.2f}", "Scenario B": f"₹{rev_b:,.2f}", "Difference (A - B)": f"{diff:+,.2f}"},
                    {"Metric": "Opportunity Score", "Scenario A": f"{res_a.get('opportunity_score', 0):.1f}", "Scenario B": f"{res_b.get('opportunity_score', 0):.1f}", "Difference (A - B)": f"{res_a.get('opportunity_score', 0) - res_b.get('opportunity_score', 0):+.1f}"},
                    {"Metric": "Risk Level", "Scenario A": res_a.get("risk_level"), "Scenario B": res_b.get("risk_level"), "Difference (A - B)": "-"},
                    {"Metric": "Strategy Allowed", "Scenario A": "✅ YES" if res_a.get("strategy_allowed") else "⛔ NO", "Scenario B": "✅ YES" if res_b.get("strategy_allowed") else "⛔ NO", "Difference (A - B)": "-"}
                ]
                st.dataframe(pd.DataFrame(comp_rows), width="stretch", hide_index=True)

    # --------------------------------------------------------------------------
    # TAB 3: 📈 Sensitivity Analysis & Failure Matrix
    # --------------------------------------------------------------------------
    with sim_tab3:
        st.markdown("<div class=\"section-title\">📈 Transaction Amount Sensitivity Analysis</div>", unsafe_allow_html=True)
        st.caption("Evaluate how expected revenue scales across different ticket sizes under current recovery conditions.")

        amounts_test = [1000.0, 5000.0, 10000.0, 25000.0, 50000.0]
        sens_data = []
        for a_val in amounts_test:
            p_test = {"amount": a_val, "payment_method": pm, "failure_reason": fr, "previous_payments": pp, "previous_failures": pf, "days_since_last_payment": ds, "subscription": sub, "strategy": selected_strategy}
            r_val, s_ok, _ = run_recovery_simulation_api(p_test)
            if s_ok:
                sens_data.append({
                    "Amount (₹)": a_val,
                    "Formatted Amount": f"₹{a_val:,.0f}",
                    "Expected Recovery (₹)": r_val.get("expected_recovery", 0.0),
                    "Recovery %": r_val.get("recovery_percentage", 0.0)
                })

        if sens_data:
            df_sens = pd.DataFrame(sens_data)
            sens_fig = px.line(
                df_sens,
                x="Amount (₹)",
                y="Expected Recovery (₹)",
                markers=True,
                text=[f"₹{v:,.0f}" for v in df_sens["Expected Recovery (₹)"]],
                title="Payment Amount vs Expected Recovery Yield"
            )
            sens_fig.update_traces(textposition="top left", line=dict(color="#2563EB", width=3), marker=dict(size=8, color="#1D4ED8"))
            sens_fig.update_layout(
                height=250,
                margin=dict(l=10, r=20, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="Transaction Amount (₹)", showgrid=True, gridcolor="#F1F5F9"),
                yaxis=dict(title="Expected Recovery (₹)", showgrid=True, gridcolor="#F1F5F9")
            )
            st.plotly_chart(sens_fig, width="stretch", config={"displayModeBar": False})

        st.markdown("---")
        st.markdown("<div class=\"section-title\">🔍 Failure Reason Impact Matrix</div>", unsafe_allow_html=True)
        st.caption("Examine how different failure reasons affect probability, risk, and optimal strategy for a ₹10,000 transaction.")

        matrix_reasons = ["network_timeout", "technical_error", "insufficient_balance", "authentication_failed", "expired_card", "bank_decline"]
        matrix_rows = []
        for r_name in matrix_reasons:
            p_m = {"amount": 10000.0, "payment_method": "card", "failure_reason": r_name, "previous_payments": 10, "previous_failures": 1, "days_since_last_payment": 3, "subscription": 1, "strategy": "AUTOMATIC_RETRY"}
            r_res, m_ok, _ = run_recovery_simulation_api(p_m)
            if m_ok:
                matrix_rows.append({
                    "Failure Reason": format_failure_reason(r_name),
                    "Type": "Permanent Decline" if r_name in PERMANENT_FAILURES else "Transient Issue",
                    "Recovery %": f"{r_res.get('recovery_percentage', 0.0):.1f}%",
                    "Expected Recovery": f"₹{r_res.get('expected_recovery', 0.0):,.2f}",
                    "Risk Level": format_risk_badge(r_res.get("risk_level", "MEDIUM")),
                    "Recommended Strategy": r_res.get("best_strategy_display", "N/A")
                })

        if matrix_rows:
            st.dataframe(pd.DataFrame(matrix_rows), width="stretch", hide_index=True)

    # --------------------------------------------------------------------------
    # TAB 4: 📜 Simulation History
    # --------------------------------------------------------------------------
    with sim_tab4:
        st.markdown("<div class=\"section-title\">📜 Recovery Simulation Audit History</div>", unsafe_allow_html=True)
        st.caption("Review all historical simulation modeling runs recorded in the audit database.")

        df_sims, s_ok, s_err = fetch_simulations(limit=50)
        if s_ok and not df_sims.empty:
            disp_hist = df_sims.copy()
            disp_hist["Formatted Amount"] = disp_hist["amount"].apply(lambda x: f"₹{x:,.2f}")
            disp_hist["Expected Recovery"] = disp_hist["expected_recovery"].apply(lambda x: f"₹{x:,.2f}")
            disp_hist["Created At"] = pd.to_datetime(disp_hist["created_at"]).dt.strftime("%d %b %Y, %H:%M")
            disp_hist["Allowed"] = disp_hist["strategy_allowed"].apply(lambda x: "✅ YES" if x else "⛔ BLOCKED")
            disp_hist["Failure Reason"] = disp_hist["failure_reason"].apply(format_failure_reason)
            disp_hist["Strategy"] = disp_hist["strategy"].apply(lambda x: STRATEGY_DISPLAY_MAP.get(x, x))

            st.dataframe(
                disp_hist[[
                    "simulation_id",
                    "Formatted Amount",
                    "Failure Reason",
                    "Strategy",
                    "Expected Recovery",
                    "opportunity_score",
                    "risk_level",
                    "Allowed",
                    "Created At"
                ]].rename(columns={
                    "simulation_id": "Simulation ID",
                    "Formatted Amount": "Amount",
                    "opportunity_score": "Opp Score",
                    "risk_level": "Risk"
                }),
                width="stretch",
                hide_index=True
            )

            # CSV download button
            csv_bytes = df_sims.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Simulation Audit Log (.csv)",
                data=csv_bytes,
                file_name=f"recoverai_simulation_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No simulation history records found yet. Run your first simulation above!")


def render_reports_view(df: pd.DataFrame):
    """Compliance and Audit Report Export View."""
    st.markdown("<h2 class=\"brand-title\">📄 Compliance & Audit Reports</h2><p class=\"brand-subtitle\">Export financial audit records, opportunity rankings, alert logs, and simulation runs.</p>", unsafe_allow_html=True)
    with st.container(border=True):
        if not df.empty:
            st.download_button(
                "📥 Export Full Recovery Audit Log (.csv)",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name="recoverai_audit_log.csv",
                mime="text/csv"
            )
        else:
            st.info("No decisions to export yet.")


# ==============================================================================
# Main Router
# ==============================================================================

def main():
    health = check_backend_health()
    df, api_online, error_msg = fetch_decisions()
    kpis = calculate_kpis(df)

    # Check active open alerts count for sidebar badge
    alert_summary, _, _ = fetch_alerts_summary()
    open_alerts_count = alert_summary.get("open_alerts", 0) if isinstance(alert_summary, dict) else 0
    crit_alerts_count = alert_summary.get("critical_alerts", 0) if isinstance(alert_summary, dict) else 0

    nav = render_sidebar(health, open_alerts_count=open_alerts_count)

    if not api_online:
        st.warning("⚠️ **Backend unavailable. Please start FastAPI on port 8000 using `uvicorn api.main:app --port 8000`**")

    if nav == "🏠 Dashboard":
        render_top_header(
            title="RecoverAI",
            subtitle="AI-Powered Payment Revenue Recovery, Opportunity Prioritization & Smart Alerts Platform",
            health=health
        )

        # Smart Alerts Section
        render_home_smart_alerts_section(health, alert_summary)

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class=\"section-title\" style=\"font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 0.5rem;\">📊 RECOVERY PERFORMANCE OVERVIEW</div>", unsafe_allow_html=True)
        render_kpi_cards(kpis)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        render_highest_recovery_opportunities(df)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        render_ops_charts(df, kpis)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        render_decision_details_and_rules(df)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        render_payment_ops_table(df)

    elif nav == "🚨 Smart Alerts":
        render_smart_alerts_view(health)

    elif nav == "💎 Revenue Opportunities":
        render_revenue_opportunities_page(health)

    elif nav == "🎯 Recovery Simulator":
        render_recovery_simulator_page(health)

    elif nav == "💳 Payment Operations":
        render_payment_operations_page(df, health)

    elif nav == "📊 Revenue Analytics":
        render_revenue_analytics_page(df, health)

    elif nav == "🤖 AI Decisions":
        st.markdown("<h2 class=\"brand-title\">🤖 AI Decision Intelligence</h2><p class=\"brand-subtitle\">Examine the exact decision rules and expected value calculation for every transaction.</p>", unsafe_allow_html=True)
        render_decision_details_and_rules(df)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        render_payment_ops_table(df)

    elif nav == "📄 Reports":
        render_reports_view(df)

    # Footer
    st.markdown(
        """
        <div style="margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center; color: #94A3B8; font-size: 0.75rem;">
            <div>RecoverAI &bull; Production Revenue Recovery Intelligence & Smart Alerts</div>
            <div>FastAPI (Port 8000) &bull; Streamlit Frontend &bull; Scikit-Learn Pipeline</div>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()