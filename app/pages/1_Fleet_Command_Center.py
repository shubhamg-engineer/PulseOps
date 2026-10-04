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
from app.components.status_chip import render_status_chip
from app.components.charts import render_oee_trend_chart
from app.components.empty_state import render_empty_state
from app.components.error_banner import render_error_banner

st.set_page_config(page_title="Fleet Command Center | PulseOps", page_icon="📊", layout="wide")
inject_custom_css()

# Header
st.title("📊 Fleet Command Center")
st.caption("Fleet Health Heatmap · OEE Performance · Top Priority Equipment at Risk")

as_of_ts = st.session_state.get("as_of_ts")
plant_id = st.session_state.get("plant_id", "All Plants")
period_days = st.session_state.get("period_days", 7)

# ─────────────────────────────────────────────────────────────
# 1. KPI STRIP
# ─────────────────────────────────────────────────────────────
kpis_res = api.get_fleet_kpis(period_days=period_days, plant_id=plant_id, as_of_ts=as_of_ts)
if not kpis_res.ok:
    render_error_banner(kpis_res.error)
else:
    k = kpis_res.data
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            label="Fleet OEE (A × P × Q)",
            value=format_pct(k.fleet_oee),
            delta=f"{k.oee_delta_pp:+.2f} pp vs prev",
            delta_positive=k.oee_delta_pp >= 0,
            subtext=f"Scope: {plant_id} ({period_days}d window)",
            value_color="#38bdf8"
        )
    with c2:
        render_kpi_card(
            label="Open At-Risk Alerts",
            value=str(k.open_alerts),
            delta=f"{k.critical_alerts} Critical",
            delta_positive=k.critical_alerts == 0,
            subtext="Requiring human triage",
            value_color="#f43f5e" if k.critical_alerts > 0 else "#10b981"
        )
    with c3:
        render_kpi_card(
            label="Downtime Cost Loss",
            value=format_inr(k.downtime_cost_inr),
            subtext=f"Total Unplanned: {format_hours(k.downtime_hours)}",
            value_color="#fbbf24"
        )
    with c4:
        render_kpi_card(
            label="Failures Avoided Early",
            value=str(k.failures_avoided),
            delta="100% Proactive",
            delta_positive=True,
            subtext="Converted to planned maintenance",
            value_color="#10b981"
        )

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# 2. FLEET HEALTH HEATMAP (PRD 3 Section 6.1)
# ─────────────────────────────────────────────────────────────
st.subheader("🏭 Equipment Health Heatmap")
st.caption("Visual matrix of all 25 production assets categorized by line and risk state. Click any asset to investigate.")

health_res = api.get_asset_health(plant_id=plant_id, as_of_ts=as_of_ts)
if not health_res.ok:
    render_error_banner(health_res.error)
else:
    df_h = health_res.data
    if df_h.empty:
        render_empty_state(title="No assets found", message="No assets registered under this plant filter.")
    else:
        # Group by plant and line
        plants = sorted(df_h["plant_id"].unique())
        for p in plants:
            st.markdown(f"#### 📍 {p}")
            p_df = df_h[df_h["plant_id"] == p]
            lines = sorted(p_df["line_id"].unique())

            for line in lines:
                l_df = p_df[p_df["line_id"] == line].sort_values(by="asset_id")
                st.markdown(f"**{line}**")
                
                # Render grid of asset cards
                cols = st.columns(len(l_df))
                for idx, (_, row) in enumerate(l_df.iterrows()):
                    with cols[idx]:
                        status = row["health_status"]
                        risk = row["risk_score"]
                        ast_id = row["asset_id"]
                        
                        chip_html = render_status_chip(status, size="small")
                        
                        st.markdown(
                            f"""
                            <div class="po-card" style="padding: 10px; text-align: center; margin-bottom: 6px;">
                                <div style="font-weight: 700; font-size: 0.88rem; color: #f8fafc;">{ast_id}</div>
                                <div style="font-size: 0.72rem; color: #94a3b8; margin-bottom: 6px;">{row['asset_type']}</div>
                                {chip_html}
                                <div style="font-size: 0.70rem; color: #64748b; margin-top: 6px;">
                                    Risk: <b>{risk:.2f}</b> · OEE: <b>{row['oee_7d']*100:.0f}%</b>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        if st.button("Inspect", key=f"btn_h_{ast_id}", use_container_width=True):
                            st.session_state["selected_asset_id"] = ast_id
                            st.switch_page("pages/3_Asset_Drilldown.py")
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# 3. TOP 5 AT-RISK ASSETS & SHIFT HANDOVER BRIEF
# ─────────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("🚨 Top Priority Assets at Risk")
    alerts_res = api.get_alerts(plant_id=plant_id, limit=5, as_of_ts=as_of_ts)
    if not alerts_res.ok:
        render_error_banner(alerts_res.error)
    else:
        df_al = alerts_res.data
        if df_al.empty:
            render_empty_state(icon="✅", title="No active alerts", message="All equipment operating within nominal parameters.")
        else:
            for _, al in df_al.iterrows():
                with st.container():
                    c_a1, c_a2, c_a3, c_a4 = st.columns([3, 2, 2, 2])
                    with c_a1:
                        st.markdown(f"**{al['asset_name']}** ({al['asset_id']})")
                        st.caption(f"{al['plant_id']} · {al['line_id']} · Criticality {al['criticality']}/5")
                    with c_a2:
                        st.markdown(render_status_chip(al['health_status']), unsafe_allow_html=True)
                        st.caption(f"Risk: **{al['risk_score']:.2f}** · Rank: **{al['priority_score']}**")
                    with c_a3:
                        st.markdown(f"**{al['predicted_failure_mode']}**")
                        st.caption(f"Window: ~{al['predicted_window_hrs']}h")
                    with c_a4:
                        if st.button("Investigate 🔍", key=f"inv_{al['alert_id']}", use_container_width=True):
                            st.session_state["selected_asset_id"] = al["asset_id"]
                            st.session_state["selected_alert_id"] = al["alert_id"]
                            st.switch_page("pages/3_Asset_Drilldown.py")
                    st.markdown("<hr style='margin: 8px 0; border-color: #1e293b;'>", unsafe_allow_html=True)

with col_right:
    st.subheader("📋 Shift Handover Intelligence Brief")
    st.caption("AI-generated briefing summarizing active risks, critical actions, and 24h operational recommendations.")
    
    if st.button("Generate Handover Brief ⚡", type="primary", use_container_width=True):
        with st.spinner("Compiling fleet metrics and generating shift report..."):
            brief_q = f"Provide a concise shift handover brief for {plant_id}. Summarize open critical equipment risks, root causes, and recommended maintenance priorities for the next shift."
            brief_res = api.ask_agent(brief_q, as_of_ts=as_of_ts)
            if brief_res.ok:
                st.session_state["shift_brief_text"] = brief_res.data.answer_markdown
            else:
                st.error("Could not generate brief.")

    brief_text = st.session_state.get("shift_brief_text")
    if brief_text:
        st.markdown(
            f"""
            <div style="background-color: #151e2e; border: 1px solid #1e293b; border-radius: 8px; padding: 14px; max-height: 280px; overflow-y: auto; font-size: 0.88rem;">
                {brief_text}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("Click 'Generate Handover Brief' above to draft the operational transition report.")
