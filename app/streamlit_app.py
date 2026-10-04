import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from datetime import datetime, timedelta, timezone
import streamlit as st

from app.services import api
from app.services.normalize import format_display_time, to_utc_datetime
from app.components.theme import inject_custom_css

UTC = timezone.utc

# Page Config
st.set_page_config(
    page_title="PulseOps | Predictive Maintenance & OEE Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global styles
inject_custom_css()

# Verify backend connectivity
backend_res = api.get_backend_info()
if not backend_res.ok:
    st.error("🚨 Cannot connect to PulseOps data backend. Please ensure the local database or Snowflake connection is active.")
    if st.button("Retry Connection"):
        st.rerun()
    st.stop()

# Initialize session state keys (PRD 3 Section 7)
defaults = {
    "plant_id": "All Plants",
    "period_days": 7,
    "as_of_ts": backend_res.data["as_of_default"],
    "selected_asset_id": "AST_101",
    "selected_alert_id": None,
    "chat_messages": [],
    "chat_session_id": "session_user_01",
    "demo_outage_enabled": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Sync demo outage toggle
api.set_demo_outage(st.session_state["demo_outage_enabled"])

# ─────────────────────────────────────────────────────────────
# SIDEBAR SHELL (PRD 3 Section 6.0)
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ PulseOps")
    st.caption("Predictive Maintenance & OEE Command Center")

    # Backend Badge & Freshness Indicator
    fresh_res = api.get_data_freshness(st.session_state["as_of_ts"])
    is_stale = fresh_res.data.get("is_stale", False) if fresh_res.ok else False
    stale_mins = fresh_res.data.get("minutes_stale", 0) if fresh_res.ok else 0

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        backend_name = backend_res.data["backend"].upper()
        b_color = "#38bdf8" if backend_name == "LOCAL" else "#a855f7"
        st.markdown(
            f"""
            <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid {b_color}; border-radius: 6px; padding: 4px 8px; text-align: center;">
                <span style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase;">Backend</span><br>
                <span style="font-size: 0.82rem; font-weight: 700; color: {b_color};">{backend_name}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_b2:
        f_color = "#f43f5e" if is_stale else "#10b981"
        f_text = f"Stale ({stale_mins}m)" if is_stale else "Live (Sync)"
        st.markdown(
            f"""
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid {f_color}; border-radius: 6px; padding: 4px 8px; text-align: center;">
                <span style="font-size: 0.68rem; color: #94a3b8; text-transform: uppercase;">Telemetry</span><br>
                <span style="font-size: 0.82rem; font-weight: 700; color: {f_color};">{f_text}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # Global Filters
    st.markdown("##### 🏭 Fleet Scope")
    filters_res = api.get_filters()
    plant_options = ["All Plants"]
    if filters_res.ok:
        plant_options.extend([p["plant_id"] for p in filters_res.data["plants"]])
    
    current_plant_idx = plant_options.index(st.session_state["plant_id"]) if st.session_state["plant_id"] in plant_options else 0
    selected_plant = st.selectbox("Operating Facility:", plant_options, index=current_plant_idx)
    st.session_state["plant_id"] = selected_plant

    period_days = st.select_slider(
        "Analysis Timeframe:",
        options=[7, 14, 30],
        value=st.session_state["period_days"],
        format_func=lambda x: f"Last {x} Days"
    )
    st.session_state["period_days"] = period_days

    st.markdown("---")

    # Replay Clock (Time Travel Scrubber - PRD 3 Section 9.1)
    st.markdown("##### ⏱️ Replay Clock (As-Of Time)")
    st.caption("Scrub time to observe failure signatures developing before alert generation.")
    
    default_latest = backend_res.data["as_of_default"]
    current_as_of = st.session_state.get("as_of_ts", default_latest)
    
    # Calculate offset in hours from dataset latest
    total_range_hours = 14 * 24 # 14 days back
    hours_back = int((default_latest - current_as_of).total_seconds() / 3600.0)
    hours_back = max(0, min(total_range_hours, hours_back))

    slider_val = st.slider(
        "Rewind Telemetry (Hours):",
        min_value=0,
        max_value=total_range_hours,
        value=hours_back,
        step=6,
        help="0 = Latest dataset reading (2026-09-29 23:55 UTC)"
    )
    
    new_as_of = default_latest - timedelta(hours=slider_val)
    st.session_state["as_of_ts"] = new_as_of
    
    st.markdown(
        f"""
        <div style="background: #0f172a; padding: 6px 10px; border-radius: 4px; border: 1px solid #1e293b; font-size: 0.78rem;">
            <span style="color: #94a3b8;">Clock Active:</span><br>
            <b style="color: #38bdf8;">{format_display_time(new_as_of)}</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # Demo Quick Actions (PRD 3 Section 9.10)
    st.markdown("##### 🎭 Demo Controls")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("⏮️ Jump to AST_101 Story", use_container_width=True, help="Scrub clock to 48h before AST_101 bearing failure"):
            st.session_state["selected_asset_id"] = "AST_101"
            st.session_state["as_of_ts"] = default_latest - timedelta(hours=48)
            st.rerun()
    with col_d2:
        if st.button("🔄 Reset Clock", use_container_width=True):
            st.session_state["as_of_ts"] = default_latest
            st.session_state["demo_outage_enabled"] = False
            st.rerun()

    # Outage Simulation Toggle (PRD 3 Section 9.7)
    outage_toggle = st.toggle("Simulate Sensor Outage", value=st.session_state["demo_outage_enabled"])
    if outage_toggle != st.session_state["demo_outage_enabled"]:
        st.session_state["demo_outage_enabled"] = outage_toggle
        api.set_demo_outage(outage_toggle)
        st.rerun()

# ─────────────────────────────────────────────────────────────
# WELCOME HERO & NAVIGATION OVERVIEW
# ─────────────────────────────────────────────────────────────
st.title("⚡ PulseOps Command Center")
st.markdown(
    """
    **Industrial OT Telemetry & Predictive Maintenance Intelligence Platform**  
    Select a module from the left sidebar navigation to begin operations:
    """
)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        """
        <div class="po-card">
            <h4>📊 1. Fleet Command Center</h4>
            <p style="font-size: 0.88rem; color: #94a3b8;">High-level overview of fleet OEE, active risk alerts, downtime financial losses, and equipment health heatmap.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Open Fleet Command Center ➡️", use_container_width=True):
        st.switch_page("pages/1_Fleet_Command_Center.py")

with col2:
    st.markdown(
        """
        <div class="po-card">
            <h4>🚨 2. Ranked Alert Queue</h4>
            <p style="font-size: 0.88rem; color: #94a3b8;">Priority-ranked predictive alerts triaged by risk score, machine criticality, and hourly downtime cost impact.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Open Alert Queue ➡️", use_container_width=True):
        st.switch_page("pages/2_Alert_Queue.py")

with col3:
    st.markdown(
        """
        <div class="po-card">
            <h4>🔍 3. Asset Drilldown & Telemetry</h4>
            <p style="font-size: 0.88rem; color: #94a3b8;">4-channel synchronized sensor graphs, shaded failure window, explainability signals, and maintenance history.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Open Asset Drilldown ➡️", use_container_width=True):
        st.switch_page("pages/3_Asset_Drilldown.py")

col4, col5, col6 = st.columns(3)
with col4:
    st.markdown(
        """
        <div class="po-card">
            <h4>🤖 4. Ask PulseOps (AI Agent)</h4>
            <p style="font-size: 0.88rem; color: #94a3b8;">Natural language root-cause investigation with verified citations, transparent SQL execution, and safety guardrails.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Open AI Agent Chat ➡️", use_container_width=True):
        st.switch_page("pages/4_Ask_PulseOps.py")

with col5:
    st.markdown(
        """
        <div class="po-card">
            <h4>📈 5. OEE & ROI Impact</h4>
            <p style="font-size: 0.88rem; color: #94a3b8;">Availability/Performance/Quality trends and interactive simulation of downtime avoided and net ₹ financial savings.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Open OEE & Impact ➡️", use_container_width=True):
        st.switch_page("pages/5_OEE_and_Impact.py")

with col6:
    st.markdown(
        """
        <div class="po-card">
            <h4>🛠️ 6. Work Orders Registry</h4>
            <p style="font-size: 0.88rem; color: #94a3b8;">Audited repository of human-approved preventive work orders with cost savings tracking and CSV export.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("Open Work Orders ➡️", use_container_width=True):
        st.switch_page("pages/6_Work_Orders.py")

# Quick KPI Snapshot
st.markdown("---")
st.markdown("### 🌐 Live Fleet Snapshot")
kpis_res = api.get_fleet_kpis(
    period_days=st.session_state["period_days"],
    plant_id=st.session_state["plant_id"],
    as_of_ts=st.session_state["as_of_ts"]
)
if kpis_res.ok:
    k = kpis_res.data
    k_col1, k_col2, k_col3, k_col4 = st.columns(4)
    with k_col1:
        st.metric("Fleet OEE", f"{k.fleet_oee*100:.1f}%", f"{k.oee_delta_pp:+.2f} pp")
    with k_col2:
        st.metric("Open High-Risk Alerts", f"{k.open_alerts}", f"{k.critical_alerts} Critical", delta_color="inverse")
    with k_col3:
        st.metric("Total Downtime Loss", f"₹{k.downtime_cost_inr:,.0f}", f"{k.downtime_hours:.1f} hrs")
    with k_col4:
        st.metric("Failures Avoided Early", f"{k.failures_avoided}", "Proactive Intervention")
