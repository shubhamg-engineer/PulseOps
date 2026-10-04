import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from datetime import timedelta
import streamlit as st
import pandas as pd
from app.services import api
from app.components.theme import inject_custom_css, format_inr, format_pct, format_hours
from app.components.status_chip import render_status_chip
from app.components.risk_gauge import render_risk_gauge
from app.components.charts import render_sensor_telemetry_chart, render_top_signals_chart
from app.components.empty_state import render_empty_state
from app.components.error_banner import render_error_banner
from app.components.work_order_modal import open_work_order_dialog

st.set_page_config(page_title="Asset Drilldown & Telemetry | PulseOps", page_icon="🔍", layout="wide")
inject_custom_css()

as_of_ts = st.session_state.get("as_of_ts")

# Check query params for deep-link: ?asset=AST_101
query_params = st.query_params
if "asset" in query_params:
    st.session_state["selected_asset_id"] = query_params["asset"]

# Asset selector
filters_res = api.get_filters()
health_res = api.get_asset_health(as_of_ts=as_of_ts)
asset_ids = health_res.data["asset_id"].tolist() if health_res.ok and not health_res.data.empty else ["AST_101"]

current_ast = st.session_state.get("selected_asset_id", "AST_101")
if current_ast not in asset_ids:
    asset_ids.insert(0, current_ast)

c_sel1, c_sel2 = st.columns([2, 5])
with c_sel1:
    selected_asset = st.selectbox(
        "Select Machine / Asset ID:",
        options=asset_ids,
        index=asset_ids.index(current_ast)
    )
    st.session_state["selected_asset_id"] = selected_asset

# Load asset detail
detail_res = api.get_asset_detail(selected_asset, as_of_ts=as_of_ts)
if not detail_res.ok:
    render_error_banner(detail_res.error)
    st.stop()

d = detail_res.data
ast_static = d.asset

# ─────────────────────────────────────────────────────────────
# 1. ASSET HEADER & RISK GAUGE
# ─────────────────────────────────────────────────────────────
h_col1, h_col2, h_col3 = st.columns([3, 2, 2])
with h_col1:
    st.title(f"🔍 {ast_static['asset_name']}")
    st.markdown(
        f"""
        **ID:** `{d.asset['asset_id']}` · **Type:** `{d.asset['asset_type']}` · 
        **Location:** `{d.asset['plant_id']} / {d.asset['line_id']}` · 
        **Criticality:** Level `{d.asset['criticality']}/5` · 
        **Hourly Downtime Cost:** `{format_inr(d.asset['downtime_cost_per_hr_inr'])}/hr`
        """
    )
with h_col2:
    st.markdown("#### Health Status")
    st.markdown(render_status_chip(d.health_status), unsafe_allow_html=True)
    st.caption(f"7-Day OEE: **{d.oee_7d*100:.1f}%** · MTBF: **{d.mtbf_hours:.1f}h** · MTTR: **{d.mttr_hours:.1f}h**")
with h_col3:
    if d.open_alert_id:
        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
        if st.button("🛠️ Draft Work Order", type="primary", use_container_width=True):
            open_work_order_dialog(d.open_alert_id)
    else:
        st.info("No active open alert for this asset.")

# ─────────────────────────────────────────────────────────────
# 2. RISK GAUGE & EXPLAINABILITY (PRD 3 Section 6.3)
# ─────────────────────────────────────────────────────────────
g_col1, g_col2 = st.columns([2, 3])
with g_col1:
    render_risk_gauge(d.current_risk_score)
    st.markdown(
        f"""
        <div style="background-color: #151e2e; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; font-size: 0.88rem;">
            <b style="color: #38bdf8;">Root-Cause Diagnosis:</b><br>
            {d.why_flagged}
        </div>
        """,
        unsafe_allow_html=True
    )
with g_col2:
    st.markdown("##### 🔬 Anomaly Signal Attribution")
    st.caption("Telemetry drift and feature contributions triggering the predictive model.")
    top_sig_fig = render_top_signals_chart(d.top_signals)
    st.plotly_chart(top_sig_fig, use_container_width=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# 3. SYNCHRONIZED 4-CHANNEL SENSOR TELEMETRY CHART
# ─────────────────────────────────────────────────────────────
st.subheader("📈 High-Resolution Telemetry Stream (72-Hour Window)")
st.caption("Synchronized multi-channel sensor feeds: ISO vibration, housing temperature, operating RPM, and current draw. Shaded zone denotes predicted failure window.")

sensor_res = api.get_sensor_series(
    asset_id=selected_asset,
    start_ts=as_of_ts - timedelta(hours=72) if as_of_ts else None,
    end_ts=as_of_ts,
    resample="15min",
    as_of_ts=as_of_ts
)

if not sensor_res.ok:
    render_error_banner(sensor_res.error)
else:
    chart_fig = render_sensor_telemetry_chart(
        df=sensor_res.data,
        predicted_window_start=d.predicted_window_start,
        predicted_window_end=d.predicted_window_end,
        replay_ts=as_of_ts
    )
    st.plotly_chart(chart_fig, use_container_width=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# 4. MAINTENANCE HISTORY, SPARE PARTS & KNOWLEDGE DOCS
# ─────────────────────────────────────────────────────────────
t_tab1, t_tab2, t_tab3, t_tab4 = st.tabs([
    "🛠️ Maintenance History",
    "📦 Spare Parts Availability",
    "📚 Technical SOPs & Guides",
    "🤖 Ask PulseOps About This Asset"
])

with t_tab1:
    hist_res = api.get_asset_orders(selected_asset, limit=10)
    if hist_res.ok and not hist_res.data.empty:
        st.dataframe(
            hist_res.data[["order_id", "order_type", "source", "status", "created_ts", "failure_mode", "cost_inr", "technician_notes"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        render_empty_state(title="No Maintenance Records", message="No historical work orders recorded for this asset.")

with t_tab2:
    parts_res = api.get_spare_parts(selected_asset)
    if parts_res.ok and not parts_res.data.empty:
        df_p = parts_res.data.copy()
        df_p["unit_cost_inr"] = df_p["unit_cost_inr"].apply(format_inr)
        st.dataframe(df_p, use_container_width=True, hide_index=True)
    else:
        render_empty_state(title="No Spare Parts", message="No cataloged parts for this machine type.")

with t_tab3:
    docs_res = api.get_related_docs(asset_id=selected_asset, failure_mode=d.predicted_failure_mode)
    if docs_res.ok and not docs_res.data.empty:
        for _, doc in docs_res.data.iterrows():
            with st.expander(f"📖 {doc['title']} ({doc['doc_type']})"):
                st.markdown(doc["snippet"])
    else:
        st.caption("No specific technical manuals attached.")

with t_tab4:
    st.markdown(f"##### Embedded AI Root-Cause Diagnostic Assistant for `{selected_asset}`")
    prompt_q = st.text_input(f"Ask a question about {selected_asset}:", placeholder=f"What is causing vibration drift on {selected_asset}?")
    if st.button("Query AI Agent ⚡", key="btn_ask_asset"):
        if prompt_q:
            with st.spinner("Analyzing telemetry patterns and failure modes..."):
                agent_res = api.ask_agent(prompt_q, context={"asset_id": selected_asset}, as_of_ts=as_of_ts)
                if agent_res.ok:
                    ans = agent_res.data
                    st.markdown(f"**Confidence:** `{ans.confidence.upper()}`")
                    st.markdown(ans.answer_markdown)
                    if ans.sources:
                        st.markdown("**Cited Sources:** " + " · ".join([f"`{s['title']}`" for s in ans.sources]))
                else:
                    st.error(agent_res.error.message)
