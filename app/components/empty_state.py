from typing import Optional
import streamlit as st

def render_empty_state(
    icon: str = "📋",
    title: str = "No data found",
    message: str = "There are no records matching your current filter criteria.",
    action_label: Optional[str] = None
) -> bool:
    """Renders a friendly, professional empty state widget. Returns True if action button clicked."""
    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 36px 20px;
            background-color: #151e2e;
            border: 1px dashed #334155;
            border-radius: 8px;
            margin: 16px 0;
        ">
            <div style="font-size: 2.5rem; margin-bottom: 8px;">{icon}</div>
            <div style="font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-bottom: 6px;">{title}</div>
            <div style="font-size: 0.88rem; color: #94a3b8; max-width: 480px; margin: 0 auto 12px auto;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if action_label:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            return st.button(action_label, use_container_width=True)
    return False
