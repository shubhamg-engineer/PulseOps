import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from app.services import api
from app.components.theme import inject_custom_css, format_inr
from app.components.status_chip import render_status_chip
from app.components.empty_state import render_empty_state
from app.components.error_banner import render_error_banner
from app.components.work_order_modal import open_work_order_dialog

st.set_page_config(page_title="Ranked Alert Queue | PulseOps", page_icon="🚨", layout="wide")
inject_custom_css()

st.title("🚨 Predictive Maintenance Alert Queue")
st.caption("Actionable triage ranked by Priority Score = Risk × Criticality × Hourly Downtime Loss")

as_of_ts = st.session_state.get("as_of_ts")
default_plant = st.session_state.get("plant_id", "All Plants")

# ─────────────────────────────────────────────────────────────
# FILTERS & CONTROLS
# ─────────────────────────────────────────────────────────────
f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 2])
with f_col1:
    status_filter = st.selectbox(
        "Alert Status:",
        ["OPEN", "ACK", "ACTIONED", "DISMISSED", "All Statuses"],
        index=0
    )
with f_col2:
    filters_res = api.get_filters()
    plants = ["All Plants"]
    if filters_res.ok:
        plants.extend([p["plant_id"] for p in filters_res.data["plants"]])
    plant_idx = plants.index(default_plant) if default_plant in plants else 0
    selected_plant = st.selectbox("Facility:", plants, index=plant_idx)

with f_col3:
    min_risk = st.slider("Minimum Risk Score:", 0.0, 1.0, 0.0, 0.05)

with f_col4:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    bulk_ack = st.button("Bulk Acknowledge Open Alerts 📋", use_container_width=True)

# ─────────────────────────────────────────────────────────────
# LOAD ALERTS
# ─────────────────────────────────────────────────────────────
alerts_res = api.get_alerts(
    status=status_filter if status_filter != "All Statuses" else None,
    plant_id=selected_plant if selected_plant != "All Plants" else None,
    min_risk=min_risk,
    as_of_ts=as_of_ts
)

if not alerts_res.ok:
    render_error_banner(alerts_res.error)
else:
    df_al = alerts_res.data
    
    # Bulk Ack Action
    if bulk_ack and not df_al.empty:
        open_ids = df_al[df_al["status"] == "OPEN"]["alert_id"].tolist()
        for aid in open_ids:
            api.update_alert_status(aid, "ACK", actor="operator_bulk")
        st.success(f"Acknowledged {len(open_ids)} open alerts.")
        st.rerun()

    if df_al.empty:
        render_empty_state(
            icon="🎉",
            title="Alert Queue Clear",
            message="No alerts match the selected status and risk filters."
        )
    else:
        st.markdown(f"**Showing {len(df_al)} Priority-Ranked Alerts**")
        st.markdown("---")

        for idx, row in df_al.iterrows():
            aid = row["alert_id"]
            ast_id = row["asset_id"]
            
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 3])
                
                with c1:
                    st.markdown(f"**{row['asset_name']}** (`{ast_id}`)")
                    st.caption(f"{row['plant_id']} · {row['line_id']} · Cost: {format_inr(row['downtime_cost_per_hr_inr'])}/hr")
                
                with c2:
                    st.markdown(render_status_chip(row["health_status"]), unsafe_allow_html=True)
                    st.caption(f"Risk: **{row['risk_score']:.2f}** · Priority: **{row['priority_score']}**")

                with c3:
                    st.markdown(f"**{row['predicted_failure_mode']}**")
                    st.caption(f"Est. Window: **~{row['predicted_window_hrs']}h**")

                with c4:
                    signals = row["top_signals"]
                    if isinstance(signals, list) and signals:
                        sig_txt = signals[0].get("signal", "Telemetry anomaly")
                        st.markdown(f"<span style='font-size: 0.8rem; color: #94a3b8;'>Signal: {sig_txt}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='font-size: 0.8rem; color: #94a3b8;'>Multi-channel vibration drift</span>", unsafe_allow_html=True)
                    st.markdown(f"Status: **`{row['status']}`**")

                with c5:
                    b_col1, b_col2, b_col3 = st.columns(3)
                    with b_col1:
                        if st.button("Inspect 🔍", key=f"insp_{aid}", use_container_width=True):
                            st.session_state["selected_asset_id"] = ast_id
                            st.session_state["selected_alert_id"] = aid
                            st.switch_page("pages/3_Asset_Drilldown.py")
                    with b_col2:
                        if row["status"] == "OPEN":
                            if st.button("Ack 👀", key=f"ack_{aid}", use_container_width=True):
                                api.update_alert_status(aid, "ACK", actor="operator")
                                st.rerun()
                        else:
                            if st.button("Dismiss ✕", key=f"dism_{aid}", use_container_width=True):
                                api.update_alert_status(aid, "DISMISSED", actor="operator")
                                st.rerun()
                    with b_col3:
                        if st.button("Order 🛠️", key=f"wo_{aid}", type="primary", use_container_width=True):
                            open_work_order_dialog(aid)

                st.markdown("<hr style='margin: 8px 0; border-color: #1e293b;'>", unsafe_allow_html=True)
