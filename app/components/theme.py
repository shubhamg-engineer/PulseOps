from datetime import datetime
from typing import Any, Optional, Tuple
import streamlit as st
from app.services.normalize import format_display_time

# Design System Colors
COLOR_PRIMARY = "#0284c7"
COLOR_BG_DARK = "#0b0f17"
COLOR_CARD_BG = "#151e2e"
COLOR_BORDER = "#1e293b"

STATUS_META = {
    "HEALTHY": {
        "color": "#10b981",
        "bg": "rgba(16, 185, 129, 0.12)",
        "border": "#10b981",
        "icon": "✓",
        "label": "Healthy"
    },
    "WATCH": {
        "color": "#facc15",
        "bg": "rgba(250, 204, 21, 0.12)",
        "border": "#facc15",
        "icon": "●",
        "label": "Watch"
    },
    "AT_RISK": {
        "color": "#f97316",
        "bg": "rgba(249, 115, 22, 0.14)",
        "border": "#f97316",
        "icon": "▲",
        "label": "At Risk"
    },
    "CRITICAL": {
        "color": "#f43f5e",
        "bg": "rgba(244, 63, 94, 0.14)",
        "border": "#f43f5e",
        "icon": "✖",
        "label": "Critical"
    },
    # Alert Statuses
    "OPEN": {
        "color": "#f43f5e",
        "bg": "rgba(244, 63, 94, 0.12)",
        "border": "#f43f5e",
        "icon": "🚨",
        "label": "OPEN"
    },
    "ACK": {
        "color": "#38bdf8",
        "bg": "rgba(56, 189, 248, 0.12)",
        "border": "#38bdf8",
        "icon": "👀",
        "label": "ACKNOWLEDGED"
    },
    "ACTIONED": {
        "color": "#10b981",
        "bg": "rgba(16, 185, 129, 0.12)",
        "border": "#10b981",
        "icon": "🔧",
        "label": "ACTIONED"
    },
    "DISMISSED": {
        "color": "#94a3b8",
        "bg": "rgba(148, 163, 184, 0.12)",
        "border": "#94a3b8",
        "icon": "✕",
        "label": "DISMISSED"
    }
}

def format_inr(amount: Optional[float]) -> str:
    """Format currency with Indian comma grouping (e.g. ₹12,34,500)."""
    if amount is None:
        return "₹0"
    amt = float(amount)
    neg = amt < 0
    amt = abs(amt)
    
    s = f"{amt:,.0f}"
    # Standard format: ₹ + number
    return f"{'-' if neg else ''}₹{s}"

def format_pct(value: Optional[float]) -> str:
    """Format 0.0 - 1.0 float as percentage (e.g. 90.8%)."""
    if value is None:
        return "0.0%"
    return f"{float(value) * 100.0:.1f}%"

def format_hours(hours: Optional[float]) -> str:
    """Format duration in hours (e.g. 45.2 h)."""
    if hours is None:
        return "0.0 h"
    return f"{float(hours):.1f} h"

def get_status_style(status_key: str) -> dict:
    key = str(status_key).upper()
    return STATUS_META.get(key, {
        "color": "#94a3b8",
        "bg": "rgba(148, 163, 184, 0.10)",
        "border": "#64748b",
        "icon": "•",
        "label": str(status_key)
    })

def inject_custom_css():
    """Inject global CSS tokens for consistent PulseOps appearance."""
    st.markdown(
        """
        <style>
        /* Card container */
        .po-card {
            background-color: #151e2e;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }
        /* Metric Card */
        .po-kpi-card {
            background-color: #151e2e;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 14px 18px;
            display: flex;
            flex-direction: column;
            justify_content: space-between;
            min-height: 105px;
            transition: border-color 0.2s;
        }
        .po-kpi-card:hover {
            border-color: #0284c7;
        }
        .po-kpi-label {
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
            font-weight: 600;
        }
        .po-kpi-value {
            font-size: 1.85rem;
            font-weight: 700;
            color: #f8fafc;
            line-height: 1.2;
            margin: 4px 0;
        }
        .po-kpi-sub {
            font-size: 0.78rem;
            color: #64748b;
        }
        /* Status badge */
        .po-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.03em;
        }
        /* Citation chip */
        .po-chip {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: #1e293b;
            border: 1px solid #334155;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            color: #38bdf8;
            margin: 2px;
        }
        /* Header pill */
        .po-header-pill {
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.78rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
