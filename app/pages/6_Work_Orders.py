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
from app.components.empty_state import render_empty_state
from app.components.error_banner import render_error_banner

st.set_page_config(page_title="Work Orders Registry | PulseOps", page_icon="🛠️", layout="wide")
inject_custom_css()

st.title("🛠️ Maintenance Work Orders Registry")
st.caption("Human-in-the-loop audited maintenance authorizations, execution status, and verified cost avoidance.")

# Top Controls
c_f1, c_f2, c_f3 = st.columns([2, 2, 2])
with c_f1:
    source_filter = st.selectbox(
        "Order Source:",
        ["PULSEOPS", "ALL"],
        index=0
    )
with c_f2:
    status_filter = st.selectbox(
        "Order Status:",
        ["ALL", "SCHEDULED", "COMPLETED"],
        index=0
    )

# Load Orders
orders_res = api.list_work_orders(source=source_filter, limit=100)
if not orders_res.ok:
    render_error_banner(orders_res.error)
else:
    df_wo = orders_res.data
    if status_filter != "ALL" and not df_wo.empty and "status" in df_wo.columns:
        df_wo = df_wo[df_wo["status"] == status_filter]

    with c_f3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if not df_wo.empty:
            csv_data = df_wo.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Export CSV",
                data=csv_data,
                file_name="pulseops_work_orders_registry.csv",
                mime="text/csv",
                use_container_width=True
            )

    st.markdown("---")

    if df_wo.empty:
        render_empty_state(
            icon="📝",
            title="No Work Orders Found",
            message="No maintenance orders match the current filter selection. Authorize an alert from the Alert Queue to generate an order."
        )
    else:
        st.markdown(f"**Registry Total: {len(df_wo)} Work Orders**")
        
        # Display table
        display_df = df_wo.copy()
        if "estimated_cost_avoided_inr" in display_df.columns:
            display_df["cost_avoided_display"] = display_df["estimated_cost_avoided_inr"].apply(format_inr)
            
        cols_to_show = [
            "order_id", "asset_id", "order_type", "source", "status",
            "created_ts", "approved_by", "risk_score_at_draft", "cost_avoided_display"
        ]
        available_cols = [c for c in cols_to_show if c in display_df.columns]

        st.dataframe(
            display_df[available_cols],
            use_container_width=True,
            hide_index=True
        )

        # Highlight recent approved order
        last_ord = st.session_state.get("last_approved_order")
        if last_ord:
            st.info(f"💡 Most recently authorized order in current session: **{last_ord}**")
