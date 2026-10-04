import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from app.services import api
from app.services.contracts import AgentResponse
from app.components.theme import inject_custom_css
from app.components.work_order_modal import open_work_order_dialog

st.set_page_config(page_title="Ask PulseOps AI | PulseOps", page_icon="🤖", layout="wide")
inject_custom_css()

st.title("🤖 Ask PulseOps — Reliability & Root-Cause AI Agent")
st.caption("Industrial natural language investigation with verifiable citations, transparent SQL evidence, and governance guardrails.")

as_of_ts = st.session_state.get("as_of_ts")

# Initialize chat session history
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Top controls
c_top1, c_top2 = st.columns([5, 1])
with c_top2:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state["chat_history"] = []
        st.rerun()

# Starter Questions (PRD 3 Section 6.4 & agent_questions.yaml)
st.markdown("##### 💡 Suggested Questions")
starters = [
    "What is the overall fleet OEE?",
    "What is the OEE breakdown by plant?",
    "Which 5 assets have the highest downtime cost loss?",
    "What is the fleet MTBF and MTTR reliability score?",
    "Why is AST_101 at risk and what is its predicted failure mode?",
    "How do I replace bearing on CNC machines?",
    "What is the weather forecast in Mumbai today?" # Guardrail test
]

col_s = st.columns(len(starters))
clicked_prompt = None
for i, q in enumerate(starters):
    with col_s[i]:
        label = q if len(q) < 32 else q[:30] + "…"
        if st.button(label, key=f"starter_{i}", help=q, use_container_width=True):
            clicked_prompt = q

# Display Chat History
st.markdown("---")
for i, msg in enumerate(st.session_state["chat_history"]):
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            resp: AgentResponse = msg.get("response")
            if resp:
                # Warning banner (e.g. Outage simulation)
                if resp.warnings:
                    for w in resp.warnings:
                        st.warning(f"⚠️ {w}")

                # Confidence Badge
                conf_color = "#10b981" if resp.confidence == "high" else ("#facc15" if resp.confidence == "medium" else "#f43f5e")
                st.markdown(
                    f"""
                    <div style="margin-bottom: 8px;">
                        <span class="po-badge" style="background: rgba(0,0,0,0.3); border: 1px solid {conf_color}; color: {conf_color};">
                            Confidence: {resp.confidence.upper()}
                        </span>
                        <span style="font-size: 0.75rem; color: #64748b; margin-left: 8px;">
                            Latency: {resp.latency_ms} ms
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Refusal card or Answer
                if resp.refused:
                    st.markdown(
                        f"""
                        <div style="background-color: rgba(244, 63, 94, 0.08); border-left: 4px solid #f43f5e; padding: 12px; border-radius: 4px; margin-bottom: 8px;">
                            <b style="color: #f43f5e;">🛡️ Guardrail Restriction:</b> {resp.refusal_reason or 'Operating scope restriction.'}<br>
                            <span style="color: #f8fafc;">{resp.answer_markdown}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(resp.answer_markdown)

                # Citation Chips
                if resp.sources:
                    chips_html = "".join([
                        f"<span class='po-chip'>📄 {s['title']}</span>" if s.get('type') == 'document'
                        else f"<span class='po-chip' style='color: #10b981;'>📊 {s['title']}</span>"
                        for s in resp.sources
                    ])
                    st.markdown(f"<div style='margin-top: 6px;'><b>Sources:</b> {chips_html}</div>", unsafe_allow_html=True)

                # Evidence & SQL Used Expander
                if resp.sql_used:
                    with st.expander("🔍 Verifiable SQL Evidence Executed"):
                        for sql in resp.sql_used:
                            st.code(sql, language="sql")

                # Suggested Actions
                if resp.suggested_actions:
                    st.markdown("##### Suggested Operational Actions")
                    act_cols = st.columns(len(resp.suggested_actions))
                    for idx, act in enumerate(resp.suggested_actions):
                        with act_cols[idx]:
                            msg_key = msg.get("id", f"msg_{i}")
                            if act.get("type") == "create_work_order":
                                if st.button(f"🛠️ {act.get('label')}", key=f"act_{msg_key}_{idx}"):
                                    open_work_order_dialog("ALT_001")
                            elif act.get("type") == "open_asset":
                                if st.button(f"🔍 {act.get('label')}", key=f"act_{msg_key}_{idx}"):
                                    st.session_state["selected_asset_id"] = act.get("asset_id")
                                    st.switch_page("app/pages/3_Asset_Drilldown.py")

                # Follow-up Suggestions
                if resp.follow_ups:
                    st.markdown("<div style='font-size: 0.8rem; color: #94a3b8; margin-top: 10px;'><b>Follow-up Suggestions:</b></div>", unsafe_allow_html=True)
                    f_cols = st.columns(len(resp.follow_ups))
                    for f_idx, f_text in enumerate(resp.follow_ups):
                        with f_cols[f_idx]:
                            msg_key = msg.get("id", f"msg_{i}")
                            if st.button(f_text, key=f"follow_{msg_key}_{f_idx}", use_container_width=True):
                                clicked_prompt = f_text

# Handle Input
user_input = st.chat_input("Ask about equipment health, telemetry drift, OEE metrics, or maintenance SOPs...")
prompt_to_send = clicked_prompt or user_input

if prompt_to_send:
    # Append user prompt
    st.session_state["chat_history"].append({
        "id": f"u_{len(st.session_state['chat_history'])}",
        "role": "user",
        "content": prompt_to_send
    })
    
    with st.chat_message("user"):
        st.markdown(prompt_to_send)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing operational telemetry and executing analytical queries..."):
            agent_res = api.ask_agent(
                question=prompt_to_send,
                session_id=st.session_state.get("chat_session_id", "session_01"),
                as_of_ts=as_of_ts
            )
            if agent_res.ok:
                resp_data = agent_res.data
                st.session_state["chat_history"].append({
                    "id": f"a_{len(st.session_state['chat_history'])}",
                    "role": "assistant",
                    "content": resp_data.answer_markdown,
                    "response": resp_data
                })
                st.rerun()
            else:
                st.error(f"Agent failed to respond: {agent_res.error.message}")
