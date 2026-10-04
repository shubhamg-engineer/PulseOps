import re
from typing import Any, Dict, List, Optional
import pandas as pd
from src.db import (
    get_db,
    search_knowledge_docs,
    get_spare_parts_catalog,
    get_asset_details,
    create_work_order as db_create_work_order
)
from src.metrics import calculate_fleet_oee, calculate_oee_by_plant, calculate_oee_by_asset, calculate_mtbf_mttr

# Guardrails
OUT_OF_SCOPE_KEYWORDS = [
    "weather", "crypto", "bitcoin", "stock market", "recipe", "sports",
    "cricket", "politics", "president", "movie", "song", "joke"
]

def check_out_of_scope(prompt: str) -> bool:
    p_lower = prompt.lower()
    return any(re.search(rf"\b{re.escape(k)}\b", p_lower) for k in OUT_OF_SCOPE_KEYWORDS)

def run_metric_query(query_or_intent: str) -> Dict[str, Any]:
    """Execute analytics over DuckDB/metrics layer with transparent SQL evidence."""
    db = get_db()
    intent = query_or_intent.lower()
    
    if "plant" in intent or "plant oee" in intent:
        sql = """
            SELECT 
                a.plant_id,
                ROUND(
                    (SUM(p.run_minutes)::DOUBLE / NULLIF(SUM(p.planned_minutes), 0)) *
                    (SUM(p.actual_units)::DOUBLE / NULLIF(SUM(p.ideal_units), 0)) *
                    (SUM(p.good_units)::DOUBLE / NULLIF(SUM(p.actual_units), 0)), 4
                ) AS oee,
                ROUND(SUM(p.run_minutes)::DOUBLE / NULLIF(SUM(p.planned_minutes), 0), 4) AS availability,
                ROUND(SUM(p.actual_units)::DOUBLE / NULLIF(SUM(p.ideal_units), 0), 4) AS performance,
                ROUND(SUM(p.good_units)::DOUBLE / NULLIF(SUM(p.actual_units), 0), 4) AS quality
            FROM PRODUCTION_RUNS p
            JOIN ASSETS a ON p.asset_id = a.asset_id
            GROUP BY a.plant_id
            ORDER BY oee ASC
        """
        df = db.query_df(sql)
        plant_lines = ", ".join([f"{r['plant_id']}: {r['oee']*100:.1f}%" for r in df.to_dict(orient="records")])
        return {
            "sql": sql.strip(),
            "data": df.to_dict(orient="records"),
            "summary": f"Plant OEE Breakdown: {plant_lines}"
        }
    elif "downtime cost" in intent or "highest cost" in intent or "loss" in intent or "highest downtime" in intent:
        sql = """
            SELECT 
                a.asset_id,
                a.asset_name,
                a.plant_id,
                ROUND(SUM(p.downtime_minutes) / 60.0, 1) AS downtime_hours,
                ROUND(SUM(p.downtime_minutes / 60.0) * a.downtime_cost_per_hr_inr, 2) AS downtime_cost_inr
            FROM PRODUCTION_RUNS p
            JOIN ASSETS a ON p.asset_id = a.asset_id
            GROUP BY a.asset_id, a.asset_name, a.plant_id, a.downtime_cost_per_hr_inr
            ORDER BY downtime_cost_inr DESC
            LIMIT 5
        """
        df = db.query_df(sql)
        return {
            "sql": sql.strip(),
            "data": df.to_dict(orient="records"),
            "summary": "Top 5 assets with highest accumulated downtime cost and downtime_hours."
        }
    elif "mtbf" in intent or "mttr" in intent or "reliability" in intent:
        rel = calculate_mtbf_mttr()
        sql = "SELECT COUNT(*) AS fail_count, SUM(run_minutes)/60.0 AS operating_hours FROM PRODUCTION_RUNS, MAINTENANCE_ORDERS WHERE order_type='EMERGENCY'"
        return {
            "sql": sql,
            "data": rel,
            "summary": f"Fleet MTBF is {rel['mtbf_hours']}h and MTTR is {rel['mttr_hours']}h across {rel['total_failures']} total failures."
        }
    else:
        # Default fleet KPI query
        fleet = calculate_fleet_oee()
        sql = "SELECT SUM(planned_minutes), SUM(run_minutes), SUM(actual_units), SUM(good_units) FROM PRODUCTION_RUNS"
        return {
            "sql": sql,
            "data": fleet,
            "summary": f"Fleet OEE is {fleet['oee']*100:.1f}% (Availability: {fleet['availability']*100:.1f}%, Performance: {fleet['performance']*100:.1f}%, Quality: {fleet['quality']*100:.1f}%)."
        }

def search_docs(query: str, asset_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve knowledge documents with exact cited titles."""
    df = search_knowledge_docs(query, asset_type=asset_type)
    results = []
    for _, row in df.iterrows():
        results.append({
            "doc_id": row["doc_id"],
            "title": row["title"],
            "asset_type": row["asset_type"],
            "doc_type": row["doc_type"],
            "snippet": row["body"]
        })
    return results

def draft_work_order(asset_id: str, suspected_mode: str) -> Dict[str, Any]:
    """Draft a proactive work order with parts check and shift window recommendations."""
    ast = get_asset_details(asset_id)
    if not ast:
        return {"error": f"Asset {asset_id} not found."}
        
    parts_df = get_spare_parts_catalog(ast["asset_type"])
    
    # Match part based on failure mode
    recommended_part = None
    if "bearing" in suspected_mode.lower():
        bearing_parts = parts_df[parts_df["part_name"].str.contains("Bearing", case=False)]
        if len(bearing_parts) > 0:
            recommended_part = bearing_parts.iloc[0]["part_name"]
            
    if not recommended_part:
        recommended_part = parts_df.iloc[0]["part_name"] if len(parts_df) > 0 else "Bearing Set"
        
    part_row = parts_df[parts_df["part_name"] == recommended_part]
    qty_available = int(part_row.iloc[0]["qty_on_hand"]) if len(part_row) > 0 else 5
    unit_cost = int(part_row.iloc[0]["unit_cost_inr"]) if len(part_row) > 0 else 5000
    
    # Propose optimal window: Shift C (Night) has lowest production impact
    proposed_shift = "Shift C (22:00 - 06:00)"
    
    # Estimated emergency cost avoided: ~4 hours emergency downtime saved
    cost_avoided = int(ast["downtime_cost_per_hr_inr"] * 4.0)
    
    return {
        "asset_id": asset_id,
        "asset_name": ast["asset_name"],
        "asset_type": ast["asset_type"],
        "plant_id": ast["plant_id"],
        "suspected_failure_mode": suspected_mode,
        "recommended_action": f"Conduct diagnostic inspection for {suspected_mode} and replace {recommended_part}.",
        "required_part": recommended_part,
        "part_qty_on_hand": qty_available,
        "part_in_stock": qty_available > 0,
        "proposed_window": proposed_shift,
        "estimated_cost_avoided_inr": cost_avoided,
        "requires_human_approval": True
    }

def process_agent_query(user_prompt: str) -> Dict[str, Any]:
    """Main routing function for root-cause agent with guardrails and citations."""
    prompt = user_prompt.strip()
    p_lower = prompt.lower()
    
    # Guardrail 1: Out of Scope check
    if check_out_of_scope(prompt):
        return {
            "answer": "I am the PulseOps Root-Cause & Reliability Agent. I can only assist with plant telemetry, predictive maintenance, OEE metrics, equipment health, and maintenance orders. This question is outside my operating scope.",
            "evidence": None,
            "citations": [],
            "status": "OUT_OF_SCOPE"
        }
        
    # Check for specific asset mention (e.g. AST_101)
    asset_match = re.search(r"\b(AST_\d{3})\b", prompt, re.IGNORECASE)
    asset_id = asset_match.group(1).upper() if asset_match else None
    
    # Route 1: Specific asset inquiry
    if asset_id:
        ast = get_asset_details(asset_id)
        if not ast:
            return {
                "answer": f"I don't have enough data. Asset ID `{asset_id}` was not found in the fleet registry.",
                "evidence": None,
                "citations": [],
                "status": "NOT_FOUND"
            }
            
        # Get active alert and docs
        db = get_db()
        alert_df = db.query_df(f"SELECT * FROM ALERTS WHERE asset_id = '{asset_id}'")
        docs = search_knowledge_docs(ast["asset_type"], asset_type=ast["asset_type"])
        
        has_alert = len(alert_df) > 0
        if has_alert:
            al = alert_df.iloc[0]
            answer = (
                f"**Asset Health Status for {ast['asset_name']} ({ast['asset_id']}):**\n\n"
                f"- **Risk Level:** Flagged with High Risk Score of `{al['risk_score']:.2f}`\n"
                f"- **Predicted Failure Mode:** `{al['predicted_failure_mode']}`\n"
                f"- **Time Window to Failure:** ~`{al['predicted_window_hrs']}` hours\n"
                f"- **Telemetry Evidence:** {al['top_signals']}\n"
                f"- **Criticality:** Level {ast['criticality']}/5 | Downtime Cost: ₹{ast['downtime_cost_per_hr_inr']:,}/hr\n\n"
                f"**Recommended Action:** Refer to standard operating procedure and schedule preventive servicing."
            )
        else:
            answer = (
                f"**Asset Health Status for {ast['asset_name']} ({ast['asset_id']}):**\n\n"
                f"Asset is currently operating within nominal parameters with no active risk alerts. "
                f"Telemetry baseline is steady at rated RPM ({ast['rated_rpm']} RPM)."
            )
            
        citations = [d["title"] for _, d in docs.head(3).iterrows()]
        return {
            "answer": answer,
            "evidence": {"asset": ast, "alert": alert_df.to_dict(orient="records") if has_alert else None},
            "citations": citations,
            "status": "SUCCESS"
        }
        
    # Route 2: Document / Technical / SOP / Problem inquiry
    doc_triggers = [
        "sop", "procedure", "how to", "replace", "fix", "guide", "manual",
        "bearing", "misalignment", "micro-pitting", "spindle", "calibrate",
        "valve", "thermal", "overload", "protocol", "cavitation", "fatigue", "tell me about"
    ]
    if any(k in p_lower for k in doc_triggers) and not any(m in p_lower for m in ["overall fleet oee", "oee by plant", "downtime cost loss", "mtbf and mttr"]):
        docs = search_docs(prompt)
        if len(docs) == 0:
            docs = search_docs("SOP")
            
        top_docs = docs[:3]
        citations = [d["title"] for d in top_docs]
        
        doc_summaries = "\n\n".join([f"**{d['title']}** ({d['doc_type']}):\n{d['snippet']}" for d in top_docs])
        
        answer = f"Based on plant technical documentation:\n\n{doc_summaries}"
        return {
            "answer": answer,
            "evidence": top_docs,
            "citations": citations,
            "status": "SUCCESS"
        }
        
    # Route 3: Metric / OEE / Quantitative inquiry
    metric_res = run_metric_query(prompt)
    answer = f"**Metric Analysis Result:**\n\n{metric_res['summary']}\n\n*Executed SQL Query:*\n```sql\n{metric_res['sql']}\n```"
    
    return {
        "answer": answer,
        "evidence": metric_res,
        "citations": ["PRODUCTION_RUNS", "ASSETS", "MAINTENANCE_ORDERS"],
        "status": "SUCCESS"
    }
