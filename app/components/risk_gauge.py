import streamlit as st
from app.components.theme import get_status_style
from app.services.normalize import risk_to_health_status

def render_risk_gauge(risk_score: float, label: str = "Failure Risk Score"):
    """Render a visual risk gauge with colored bands and current score pointer."""
    score = max(0.0, min(1.0, float(risk_score)))
    pct = score * 100.0
    status = risk_to_health_status(score)
    meta = get_status_style(status)

    html = f"""
    <div style="background-color: #151e2e; border: 1px solid #1e293b; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
            <span style="font-size: 0.85rem; font-weight: 600; color: #94a3b8; text-transform: uppercase;">{label}</span>
            <span style="font-size: 1.4rem; font-weight: 700; color: {meta['color']};">
                {score:.2f} <span style="font-size: 0.8rem; font-weight: 500;">({meta['label']})</span>
            </span>
        </div>
        <!-- Multi-colored progress track -->
        <div style="height: 10px; width: 100%; background: #1e293b; border-radius: 5px; position: relative; overflow: hidden; display: flex;">
            <div style="width: 30%; background: rgba(16, 185, 129, 0.4); height: 100%; border-right: 1px solid #0f172a;"></div>
            <div style="width: 30%; background: rgba(250, 204, 21, 0.4); height: 100%; border-right: 1px solid #0f172a;"></div>
            <div style="width: 20%; background: rgba(249, 115, 22, 0.4); height: 100%; border-right: 1px solid #0f172a;"></div>
            <div style="width: 20%; background: rgba(244, 63, 94, 0.4); height: 100%;"></div>
        </div>
        <!-- Needle / Active fill indicator -->
        <div style="margin-top: 6px; height: 4px; width: 100%; background: #334155; border-radius: 2px;">
            <div style="height: 100%; width: {pct}%; background: {meta['color']}; border-radius: 2px;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.70rem; color: #64748b; margin-top: 4px;">
            <span>0.00 (Healthy)</span>
            <span>0.30 (Watch)</span>
            <span>0.60 (At Risk)</span>
            <span>0.80 (Critical)</span>
            <span>1.00</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
