import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from app.services import api
from app.components.theme import inject_custom_css, format_inr, format_pct, format_hours
from app.components.kpi_card import render_kpi_card
from app.components.charts import render_oee_trend_chart
from app.components.error_banner import render_error_banner

st.set_page_config(page_title="OEE & Impact Simulation | PulseOps", page_icon="📈", layout="wide")
inject_custom_css()

st.title("📈 OEE Analytics & ROI Impact Simulation")
st.caption("Quantifying business value: Downtime hours avoided, OEE percentage points uplift, and net INR cost savings.")

as_of_ts = st.session_state.get("as_of_ts")

# ─────────────────────────────────────────────────────────────
# 1. INTERACTIVE SIMULATION & ROI CONTROL (PRD 3 Section 6.5)
# ─────────────────────────────────────────────────────────────
st.subheader("💡 Financial ROI & Downtime Avoidance Simulator")
st.caption("Adjust the Planned Intervention Ratio assumption to observe dynamic cost savings across the fleet.")

col_slider, col_assump = st.columns([3, 2])
with col_slider:
    planned_fix_factor = st.slider(
        "Planned Fix Duration vs Unplanned Breakdown (Ratio):",
        min_value=0.10,
        max_value=0.80,
        value=0.40,
        step=0.05,
        help="A planned preventive repair takes ~40% of the time required to resolve a catastrophic breakdown."
    )
with col_assump:
    st.markdown(
        """
        <div style="background: #151e2e; border: 1px solid #1e293b; padding: 10px 14px; border-radius: 6px; font-size: 0.82rem;">
            <b>Core Assumptions:</b><br>
            • Early Detection Lead Time: ≥ 24 Hours<br>
            • Planned vs Emergency Labor Ratio: <b>{:.0f}%</b><br>
            • Historical Fleet Downtime Cost: ₹10,000–₹25,000/hr
        </div>
        """.format(planned_fix_factor * 100),
        unsafe_allow_html=True
    )

impact_res = api.get_impact_summary(planned_fix_factor=planned_fix_factor, as_of_ts=as_of_ts)
if not impact_res.ok:
    render_error_banner(impact_res.error)
else:
    summary, events_df = impact_res.data
    
    # Impact Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            label="Net Financial Savings",
            value=format_inr(summary.cost_saved_inr),
            delta="ROI Positive",
            delta_positive=True,
            subtext="From early breakdown prevention",
            value_color="#10b981"
        )
    with c2:
        render_kpi_card(
            label="Downtime Hours Avoided",
            value=format_hours(summary.downtime_avoided_hours),
            delta="Production Saved",
            delta_positive=True,
            subtext=f"Across {summary.failures_caught} caught failures",
            value_color="#38bdf8"
        )
    with c3:
        render_kpi_card(
            label="Fleet OEE Uplift",
            value=f"+{summary.oee_uplift_pp:.2f} pp",
            delta="Efficiency Gain",
            delta_positive=True,
            subtext="Percentage points improvement",
            value_color="#a855f7"
        )
    with c4:
        render_kpi_card(
            label="Median Detection Lead Time",
            value=f"{summary.median_lead_time_hours:.1f} hrs",
            delta="Target: ≥ 24h",
            delta_positive=True,
            subtext="Sufficient planning buffer",
            value_color="#f59e0b"
        )

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# 2. OEE TREND & DECOMPOSITION (A × P × Q)
# ─────────────────────────────────────────────────────────────
st.subheader("📊 Multi-Tier OEE Breakdown")

col_g1, col_g2 = st.columns([2, 5])
with col_g1:
    group_choice = st.selectbox(
        "Aggregation Level:",
        ["Fleet Overall", "By Plant", "By Production Line"],
        index=0
    )
    group_map = {"Fleet Overall": "fleet", "By Plant": "plant", "By Production Line": "line"}

trend_res = api.get_oee_trend(
    group_by=group_map[group_choice],
    period_days=st.session_state.get("period_days", 30),
    as_of_ts=as_of_ts
)

if not trend_res.ok:
    render_error_banner(trend_res.error)
else:
    oee_fig = render_oee_trend_chart(trend_res.data)
    st.plotly_chart(oee_fig, use_container_width=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# 3. FAILURE DETECTION LOG & MODEL QUALITY
# ─────────────────────────────────────────────────────────────
st.subheader("📋 Historical Failure Intervention Audit")
st.caption("Replay verification of predictive model performance against historical catastrophic breakdown events.")

if not impact_res.ok:
    st.info("No failure events loaded.")
else:
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        st.markdown(
            f"""
            <div style="background: #151e2e; border: 1px solid #1e293b; padding: 12px; border-radius: 6px; font-size: 0.85rem;">
                <b>Detection Performance:</b><br>
                • Caught Early: <b style="color: #10b981;">{summary.failures_caught}</b> / {summary.failures_total} ({summary.failures_caught/max(summary.failures_total, 1)*100:.0f}%)<br>
                • False Alarms / Week: <b>{summary.false_alarms_per_week:.1f}</b><br>
                • Median Lead Time: <b>{summary.median_lead_time_hours:.1f}h</b>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_t1:
        st.dataframe(
            events_df[["order_id", "asset_id", "asset_name", "plant_id", "created_ts", "failure_mode", "downtime_hours", "lead_time_hours", "detection_status"]],
            use_container_width=True,
            hide_index=True
        )
