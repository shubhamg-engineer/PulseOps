from typing import Optional
import streamlit as st
from app.services.contracts import ServiceError

def render_error_banner(
    error: ServiceError,
    retry_label: str = "Retry",
    show_details: bool = True
) -> bool:
    """Renders a friendly non-crashing error banner. Returns True if retry was clicked."""
    st.markdown(
        f"""
        <div style="
            background-color: rgba(244, 63, 94, 0.12);
            border: 1px solid #f43f5e;
            border-radius: 8px;
            padding: 14px 18px;
            margin: 12px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        ">
            <div>
                <span style="font-weight: 700; color: #f43f5e; margin-right: 8px;">[{error.code}]</span>
                <span style="color: #f8fafc; font-size: 0.92rem;">{error.message}</span>
                {f'<div style="font-size: 0.78rem; color: #fda4af; margin-top: 4px;">{error.detail}</div>' if show_details and error.detail else ''}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    col1, col2 = st.columns([6, 1])
    with col2:
        return st.button(f"🔄 {retry_label}", key=f"err_retry_{error.code}")
