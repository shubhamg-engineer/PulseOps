import hashlib
from typing import Any, Dict, Optional
import streamlit as st
from app.services import api
from app.services.contracts import WorkOrderDraft
from app.components.theme import format_inr

def open_work_order_dialog(alert_id: str):
    """Trigger the work order approval dialog modal for the given alert_id."""
    st.session_state["active_draft_alert_id"] = alert_id
    # Call the dialog function
    render_approval_dialog(alert_id)

@st.dialog("🛠️ Review & Approve Preventive Work Order")
def render_approval_dialog(alert_id: str):
    draft_res = api.draft_work_order(alert_id)
    if not draft_res.ok:
        st.error(f"Cannot draft work order: {draft_res.error.message}")
        if st.button("Close"):
            st.rerun()
        return

    draft: WorkOrderDraft = draft_res.data

    st.markdown(
        f"""
        <div style="background-color: #1e293b; border-left: 4px solid #38bdf8; padding: 10px 14px; border-radius: 4px; margin-bottom: 14px;">
            <div style="font-size: 0.85rem; color: #94a3b8;">ASSET REQUIRING ATTENTION</div>
            <div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc;">{draft.asset_name} ({draft.asset_id})</div>
            <div style="font-size: 0.82rem; color: #f43f5e; font-weight: 600;">Suspected Mode: {draft.suspected_failure_mode} (Risk Score: {draft.risk_score_at_draft:.2f})</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Editable Recommended Action
    rec_action = st.text_area(
        "Recommended Action / Maintenance Scope:",
        value=draft.recommended_action,
        height=75
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Estimated Labor:** `{draft.estimated_labor_hours:.1f} hours`")
        st.markdown(f"**Intervention Cost:** `{format_inr(draft.estimated_cost_inr)}`")
    with col2:
        st.markdown(f"**Est. Downtime Cost Avoided:** <span style='color: #10b981; font-weight: bold;'>{format_inr(draft.estimated_cost_avoided_inr)}</span>", unsafe_allow_html=True)
        st.markdown(f"**Draft Reference:** `{draft.draft_id}`")

    # Parts Availability Table
    st.markdown("##### Required Spare Parts & Availability")
    if draft.parts:
        for p in draft.parts:
            avail = p.get("available", False)
            color = "#10b981" if avail else "#f43f5e"
            badge_text = "IN STOCK" if avail else f"OUT OF STOCK ({p.get('lead_time_days', 0)}d lead time)"
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px;">
                    <div>
                        <span style="font-weight: 600; color: #f8fafc;">{p.get('part_name')}</span>
                        <span style="font-size: 0.75rem; color: #64748b; margin-left: 6px;">(ID: {p.get('part_id')})</span>
                    </div>
                    <div>
                        <span style="color: {color}; font-size: 0.78rem; font-weight: 700; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; border: 1px solid {color};">
                            {badge_text}
                        </span>
                        <span style="font-size: 0.78rem; color: #94a3b8; margin-left: 8px;">Qty: {p.get('qty_on_hand')} on hand</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.caption("Standard workshop consumables only.")

    st.markdown("---")

    # Governance: Required approver name
    approver = st.text_input(
        "Approver Full Name & Title (Required for Audit Trail)*:",
        value=st.session_state.get("approver_name", "Lead Maintenance Planner S. Rao")
    )

    # Compute idempotency key
    key_src = f"{draft.alert_id}:{draft.asset_id}:{draft.suspected_failure_mode}:{rec_action}"
    idemp_key = f"{draft.alert_id}:{hashlib.md5(key_src.encode()).hexdigest()[:12]}"

    c_btn1, c_btn2 = st.columns([2, 1])
    with c_btn1:
        approve_clicked = st.button(
            "✅ Approve & Schedule Work Order",
            type="primary",
            use_container_width=True,
            disabled=not bool(approver and approver.strip())
        )
    with c_btn2:
        cancel_clicked = st.button("Cancel", use_container_width=True)

    if cancel_clicked:
        st.rerun()

    if approve_clicked:
        with st.spinner("Authorizing and committing work order to registry..."):
            # Update recommended action in draft
            draft.recommended_action = rec_action
            res = api.approve_work_order(draft, approver=approver, idempotency_key=idemp_key)
            
            if res.ok:
                st.session_state["last_approved_order"] = res.data.order_id
                # Update alert status to ACTIONED
                api.update_alert_status(draft.alert_id, "ACTIONED", actor=approver)
                
                status_note = "Existing Order Re-confirmed (Idempotent)" if res.data.already_existed else "Work Order Successfully Created"
                st.success(f"{status_note}! Assigned Order ID: **{res.data.order_id}**")
                st.markdown(f"Audit Signature: `{res.data.audit_id}` · Status: **{res.data.status}**")
                if st.button("View in Work Orders Registry 📋"):
                    st.switch_page("app/pages/6_Work_Orders.py")
            else:
                st.error(f"Approval failed: {res.error.message}")
