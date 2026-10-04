from typing import Optional
import streamlit as st

def render_kpi_card(
    label: str,
    value: str,
    subtext: str = "",
    delta: Optional[str] = None,
    delta_positive: bool = True,
    value_color: Optional[str] = None
):
    """Renders a styled KPI card in Streamlit."""
    val_style = f"color: {value_color};" if value_color else "color: #f8fafc;"
    
    delta_html = ""
    if delta is not None:
        d_color = "#10b981" if delta_positive else "#f43f5e"
        d_arrow = "▲" if delta_positive else "▼"
        delta_html = f"<span style='color: {d_color}; font-size: 0.8rem; margin-left: 8px;'>{d_arrow} {delta}</span>"

    html = f"""
    <div class="po-kpi-card">
        <div class="po-kpi-label">{label}</div>
        <div class="po-kpi-value" style="{val_style}">
            {value} {delta_html}
        </div>
        <div class="po-kpi-sub">{subtext}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
