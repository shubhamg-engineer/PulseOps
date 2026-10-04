from datetime import datetime, timedelta, timezone
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from src.config import BACKEND
from app.services.contracts import (
    AgentResponse,
    AssetDetail,
    FleetKPIs,
    ImpactSummary,
    ServiceError,
    ServiceMeta,
    ServiceResult,
    WorkOrderDraft,
    WorkOrderResult
)
from app.services.normalize import (
    to_utc_datetime
)
from app.data_access import local_duckdb

UTC = timezone.utc

# Global demo state toggle for simulating outage
_DEMO_OUTAGE_ENABLED = False

def set_demo_outage(enabled: bool):
    global _DEMO_OUTAGE_ENABLED
    _DEMO_OUTAGE_ENABLED = enabled

def is_demo_outage_enabled() -> bool:
    return _DEMO_OUTAGE_ENABLED

# Helper to execute with envelope & timing
def _wrap_call(func, *args, **kwargs) -> ServiceResult:
    start_t = time.perf_counter()
    backend_name = "snowflake" if BACKEND.lower() == "snowflake" else "local"
    try:
        data = func(*args, **kwargs)
        latency = int((time.perf_counter() - start_t) * 1000)
        return ServiceResult(
            ok=True,
            data=data,
            error=None,
            meta=ServiceMeta(backend=backend_name, latency_ms=latency)
        )
    except FileNotFoundError as e:
        latency = int((time.perf_counter() - start_t) * 1000)
        return ServiceResult(
            ok=False,
            data=None,
            error=ServiceError(code="BACKEND_UNAVAILABLE", message="Database file not found", detail=str(e)),
            meta=ServiceMeta(backend=backend_name, latency_ms=latency)
        )
    except KeyError as e:
        latency = int((time.perf_counter() - start_t) * 1000)
        return ServiceResult(
            ok=False,
            data=None,
            error=ServiceError(code="NOT_FOUND", message=f"Record not found: {e}", detail=str(e)),
            meta=ServiceMeta(backend=backend_name, latency_ms=latency)
        )
    except ValueError as e:
        latency = int((time.perf_counter() - start_t) * 1000)
        return ServiceResult(
            ok=False,
            data=None,
            error=ServiceError(code="VALIDATION_ERROR", message=str(e), detail=str(e)),
            meta=ServiceMeta(backend=backend_name, latency_ms=latency)
        )
    except Exception as e:
        latency = int((time.perf_counter() - start_t) * 1000)
        return ServiceResult(
            ok=False,
            data=None,
            error=ServiceError(code="QUERY_FAILED", message="Internal query execution failed", detail=str(e)),
            meta=ServiceMeta(backend=backend_name, latency_ms=latency)
        )

# ─────────────────────────────────────────────────────────────
# 1. get_backend_info()
# ─────────────────────────────────────────────────────────────
def get_backend_info() -> ServiceResult[Dict[str, Any]]:
    start_t = time.perf_counter()
    try:
        latest = local_duckdb.get_dataset_latest_timestamp()
        backend_name = "snowflake" if BACKEND.lower() == "snowflake" else "local"
        data = {
            "backend": backend_name,
            "warehouse": "PULSEOPS_XS_WH" if backend_name == "snowflake" else "Embedded DuckDB (In-Process)",
            "as_of_default": latest
        }
        return ServiceResult(
            ok=True,
            data=data,
            meta=ServiceMeta(backend=backend_name, latency_ms=int((time.perf_counter() - start_t) * 1000), as_of_ts=latest)
        )
    except Exception as e:
        return ServiceResult(
            ok=False,
            error=ServiceError(code="BACKEND_UNAVAILABLE", message="Cannot reach backend", detail=str(e))
        )

# ─────────────────────────────────────────────────────────────
# 2. get_data_freshness()
# ─────────────────────────────────────────────────────────────
def get_data_freshness(as_of_ts: Optional[datetime] = None) -> ServiceResult[Dict[str, Any]]:
    start_t = time.perf_counter()
    try:
        if is_demo_outage_enabled():
            # Simulated sensor outage: 185 minutes stale
            data = {
                "latest_reading_ts": datetime(2026, 9, 29, 20, 50, 0, tzinfo=UTC),
                "minutes_stale": 185,
                "is_stale": True,
                "threshold_minutes": 60
            }
        else:
            latest = local_duckdb.get_dataset_latest_timestamp()
            as_of = as_of_ts or latest
            # In historical replay mode, staleness is relative to as_of
            diff_mins = max(0, int((as_of - latest).total_seconds() / 60.0))
            data = {
                "latest_reading_ts": latest,
                "minutes_stale": diff_mins,
                "is_stale": diff_mins > 60,
                "threshold_minutes": 60
            }
        return ServiceResult(
            ok=True,
            data=data,
            meta=ServiceMeta(latency_ms=int((time.perf_counter() - start_t) * 1000))
        )
    except Exception as e:
        return ServiceResult(
            ok=False,
            error=ServiceError(code="QUERY_FAILED", message="Failed to assess data freshness", detail=str(e))
        )

# ─────────────────────────────────────────────────────────────
# 3. get_filters()
# ─────────────────────────────────────────────────────────────
def get_filters() -> ServiceResult[Dict[str, Any]]:
    return _wrap_call(local_duckdb.get_filters_data)

# ─────────────────────────────────────────────────────────────
# 4. get_fleet_kpis()
# ─────────────────────────────────────────────────────────────
def get_fleet_kpis(
    period_days: int = 7,
    plant_id: Optional[str] = None,
    as_of_ts: Optional[datetime] = None
) -> ServiceResult[FleetKPIs]:
    start_t = time.perf_counter()
    try:
        raw = local_duckdb.get_fleet_kpis_data(period_days=period_days, plant_id=plant_id, as_of_ts=as_of_ts)
        kpis = FleetKPIs(**raw)
        return ServiceResult(
            ok=True,
            data=kpis,
            meta=ServiceMeta(latency_ms=int((time.perf_counter() - start_t) * 1000), as_of_ts=kpis.as_of_ts)
        )
    except Exception as e:
        return ServiceResult(
            ok=False,
            error=ServiceError(code="QUERY_FAILED", message="Failed to compute fleet KPIs", detail=str(e))
        )

# ─────────────────────────────────────────────────────────────
# 5. get_asset_health()
# ─────────────────────────────────────────────────────────────
def get_asset_health(
    plant_id: Optional[str] = None,
    as_of_ts: Optional[datetime] = None
) -> ServiceResult[pd.DataFrame]:
    return _wrap_call(local_duckdb.get_asset_health_data, plant_id=plant_id, as_of_ts=as_of_ts)

# ─────────────────────────────────────────────────────────────
# 6. get_alerts()
# ─────────────────────────────────────────────────────────────
def get_alerts(
    status: Optional[str] = None,
    plant_id: Optional[str] = None,
    min_risk: float = 0.0,
    limit: int = 200,
    as_of_ts: Optional[datetime] = None
) -> ServiceResult[pd.DataFrame]:
    return _wrap_call(
        local_duckdb.get_alerts_data,
        status=status,
        plant_id=plant_id,
        min_risk=min_risk,
        limit=limit,
        as_of_ts=as_of_ts
    )

# ─────────────────────────────────────────────────────────────
# 7. update_alert_status()
# ─────────────────────────────────────────────────────────────
def update_alert_status(alert_id: str, status: str, actor: str = "operator") -> ServiceResult[Dict[str, Any]]:
    start_t = time.perf_counter()
    try:
        if not alert_id:
            return ServiceResult(
                ok=False,
                error=ServiceError(code="VALIDATION_ERROR", message="alert_id is required")
            )
        valid_statuses = ["OPEN", "ACK", "ACTIONED", "DISMISSED"]
        if status.upper() not in valid_statuses:
            return ServiceResult(
                ok=False,
                error=ServiceError(code="VALIDATION_ERROR", message=f"Status must be one of {valid_statuses}")
            )
        updated = local_duckdb.update_alert_status_db(alert_id, status.upper(), actor)
        if not updated:
            return ServiceResult(
                ok=False,
                error=ServiceError(code="NOT_FOUND", message=f"Alert {alert_id} not found")
            )
        return ServiceResult(
            ok=True,
            data=updated,
            meta=ServiceMeta(latency_ms=int((time.perf_counter() - start_t) * 1000))
        )
    except Exception as e:
        return ServiceResult(
            ok=False,
            error=ServiceError(code="QUERY_FAILED", message="Failed to update alert status", detail=str(e))
        )

# ─────────────────────────────────────────────────────────────
# 8. get_asset_detail()
# ─────────────────────────────────────────────────────────────
def get_asset_detail(asset_id: str, as_of_ts: Optional[datetime] = None) -> ServiceResult[AssetDetail]:
    start_t = time.perf_counter()
    try:
        if not asset_id:
            return ServiceResult(
                ok=False,
                error=ServiceError(code="VALIDATION_ERROR", message="asset_id is required")
            )
        raw = local_duckdb.get_asset_detail_data(asset_id, as_of_ts=as_of_ts)
        if not raw:
            return ServiceResult(
                ok=False,
                error=ServiceError(code="NOT_FOUND", message=f"Asset '{asset_id}' not found in fleet catalog")
            )
        detail = AssetDetail(**raw)
        return ServiceResult(
            ok=True,
            data=detail,
            meta=ServiceMeta(latency_ms=int((time.perf_counter() - start_t) * 1000), as_of_ts=detail.last_reading_ts)
        )
    except Exception as e:
        return ServiceResult(
            ok=False,
            error=ServiceError(code="QUERY_FAILED", message="Failed to load asset details", detail=str(e))
        )

# ─────────────────────────────────────────────────────────────
# 9. get_sensor_series()
# ─────────────────────────────────────────────────────────────
def get_sensor_series(
    asset_id: str,
    start_ts: Optional[datetime] = None,
    end_ts: Optional[datetime] = None,
    resample: str = "15min",
    as_of_ts: Optional[datetime] = None
) -> ServiceResult[pd.DataFrame]:
    start_t = time.perf_counter()
    try:
        if not asset_id:
            return ServiceResult(
                ok=False,
                error=ServiceError(code="VALIDATION_ERROR", message="asset_id is required")
            )
        df = local_duckdb.get_sensor_series_data(
            asset_id=asset_id,
            start_ts=start_ts,
            end_ts=end_ts,
            resample=resample,
            as_of_ts=as_of_ts
        )
        return ServiceResult(
            ok=True,
            data=df,
            meta=ServiceMeta(latency_ms=int((time.perf_counter() - start_t) * 1000))
        )
    except Exception as e:
        return ServiceResult(
            ok=False,
            error=ServiceError(code="QUERY_FAILED", message="Failed to fetch sensor series", detail=str(e))
        )

# ─────────────────────────────────────────────────────────────
# 10. get_asset_orders()
# ─────────────────────────────────────────────────────────────
def get_asset_orders(asset_id: str, limit: int = 5) -> ServiceResult[pd.DataFrame]:
    return _wrap_call(local_duckdb.get_asset_orders_data, asset_id=asset_id, limit=limit)

# ─────────────────────────────────────────────────────────────
# 11. get_spare_parts()
# ─────────────────────────────────────────────────────────────
def get_spare_parts(asset_id: str) -> ServiceResult[pd.DataFrame]:
    return _wrap_call(local_duckdb.get_spare_parts_data, asset_id=asset_id)

# ─────────────────────────────────────────────────────────────
# 12. get_related_docs()
# ─────────────────────────────────────────────────────────────
def get_related_docs(
    asset_id: Optional[str] = None,
    failure_mode: Optional[str] = None,
    limit: int = 5
) -> ServiceResult[pd.DataFrame]:
    return _wrap_call(local_duckdb.get_related_docs_data, asset_id=asset_id, failure_mode=failure_mode, limit=limit)

# ─────────────────────────────────────────────────────────────
# 13. get_oee_trend()
# ─────────────────────────────────────────────────────────────
def get_oee_trend(
    group_by: str = "fleet",
    period_days: int = 30,
    granularity: str = "day",
    as_of_ts: Optional[datetime] = None
) -> ServiceResult[pd.DataFrame]:
    return _wrap_call(
        local_duckdb.get_oee_trend_data,
        group_by=group_by,
        period_days=period_days,
        granularity=granularity,
        as_of_ts=as_of_ts
    )

# ─────────────────────────────────────────────────────────────
# 14. get_impact_summary()
# ─────────────────────────────────────────────────────────────
def get_impact_summary(
    planned_fix_factor: Optional[float] = None,
    as_of_ts: Optional[datetime] = None
) -> ServiceResult[Tuple[ImpactSummary, pd.DataFrame]]:
    start_t = time.perf_counter()
    try:
        factor = planned_fix_factor if planned_fix_factor is not None else 0.40
        summary_raw, events_df = local_duckdb.get_impact_summary_data(planned_fix_factor=factor, as_of_ts=as_of_ts)
        summary = ImpactSummary(**summary_raw)
        return ServiceResult(
            ok=True,
            data=(summary, events_df),
            meta=ServiceMeta(latency_ms=int((time.perf_counter() - start_t) * 1000))
        )
    except Exception as e:
        return ServiceResult(
            ok=False,
            error=ServiceError(code="QUERY_FAILED", message="Failed to compute impact simulation", detail=str(e))
        )

# ─────────────────────────────────────────────────────────────
# 15. ask_agent() (Structured Response - PRD 3 Section 4.3)
# ─────────────────────────────────────────────────────────────
def ask_agent(
    question: str,
    session_id: str = "default",
    context: Optional[Dict[str, Any]] = None,
    as_of_ts: Optional[datetime] = None
) -> ServiceResult[AgentResponse]:
    start_t = time.perf_counter()
    try:
        from src.agent import process_agent_query, check_out_of_scope
        
        prompt = question.strip()
        warnings = []

        # Check for simulated outage
        if is_demo_outage_enabled():
            warnings.append("SENSOR OUTAGE DETECTED: Telemetry stream is stale (> 3 hours). Predictions may be degraded.")

        # Guardrail: Check out-of-scope
        if check_out_of_scope(prompt):
            resp = AgentResponse(
                answer_markdown="I am the **PulseOps Reliability & Root-Cause Agent**. I am restricted to industrial OT telemetry, predictive maintenance, OEE metrics, equipment health, and maintenance orders. This inquiry is outside my operating scope.",
                sources=[],
                sql_used=[],
                confidence="low",
                warnings=warnings,
                refused=True,
                refusal_reason="Question contains out-of-scope topics.",
                suggested_actions=[],
                follow_ups=["What is the fleet OEE?", "Which assets have active risk alerts?", "Show maintenance history"],
                latency_ms=int((time.perf_counter() - start_t) * 1000)
            )
            return ServiceResult(ok=True, data=resp)

        # Handle specific asset context if provided
        query_text = prompt
        if context and "asset_id" in context and context["asset_id"] not in query_text:
            query_text = f"{context['asset_id']}: {query_text}"

        res = process_agent_query(query_text)
        
        # Check if asset not found
        if res.get("status") == "NOT_FOUND":
            resp = AgentResponse(
                answer_markdown=res["answer"],
                sources=[],
                sql_used=[],
                confidence="low",
                warnings=warnings,
                refused=False,
                refusal_reason=None,
                suggested_actions=[],
                follow_ups=["List all registered assets", "Show active alerts"],
                latency_ms=int((time.perf_counter() - start_t) * 1000)
            )
            return ServiceResult(ok=True, data=resp)

        # Parse sources & SQL used
        sources = []
        sql_used = []
        for cit in res.get("citations", []):
            sources.append({"type": "table" if cit.isupper() else "document", "title": str(cit), "id": str(cit)})

        ev = res.get("evidence")
        if isinstance(ev, dict) and "sql" in ev:
            sql_used.append(ev["sql"])

        # Determine suggested actions
        suggested_actions = []
        follow_ups = []
        if "AST_" in query_text:
            import re
            m = re.search(r"AST_\d{3}", query_text)
            if m:
                target_ast = m.group(0)
                suggested_actions.append({
                    "type": "create_work_order",
                    "asset_id": target_ast,
                    "label": f"Draft Work Order for {target_ast}"
                })
                suggested_actions.append({
                    "type": "open_asset",
                    "asset_id": target_ast,
                    "label": f"View {target_ast} Sensor Telemetry"
                })
                follow_ups = [
                    f"What parts are needed for {target_ast}?",
                    f"Show recent maintenance orders for {target_ast}",
                    f"What is the downtime cost of {target_ast}?"
                ]
        else:
            follow_ups = [
                "Which plant has the lowest OEE?",
                "What are the top 3 critical failure risks?",
                "What is the total downtime financial loss?"
            ]

        confidence = "medium" if warnings else "high"

        resp = AgentResponse(
            answer_markdown=res.get("answer", ""),
            sources=sources,
            sql_used=sql_used,
            confidence=confidence,
            warnings=warnings,
            refused=False,
            refusal_reason=None,
            suggested_actions=suggested_actions,
            follow_ups=follow_ups,
            latency_ms=int((time.perf_counter() - start_t) * 1000)
        )
        return ServiceResult(ok=True, data=resp)
    except Exception as e:
        return ServiceResult(
            ok=False,
            error=ServiceError(code="AGENT_ERROR", message="Agent processing failure", detail=str(e))
        )

# ─────────────────────────────────────────────────────────────
# 16. draft_work_order() (PRD 3 Section 4.4)
# ─────────────────────────────────────────────────────────────
def draft_work_order(alert_id: str) -> ServiceResult[WorkOrderDraft]:
    start_t = time.perf_counter()
    try:
        from app.data_access.local_duckdb import get_connection
        with get_connection(read_only=True) as con:
            al_df = con.execute("SELECT * FROM ALERTS WHERE alert_id = ?", [alert_id]).df()
            if al_df.empty:
                return ServiceResult(
                    ok=False,
                    error=ServiceError(code="NOT_FOUND", message=f"Alert '{alert_id}' not found")
                )
            al = al_df.iloc[0]
            asset_id = al["asset_id"]
            
            ast_df = con.execute("SELECT * FROM ASSETS WHERE asset_id = ?", [asset_id]).df()
            if ast_df.empty:
                return ServiceResult(
                    ok=False,
                    error=ServiceError(code="NOT_FOUND", message=f"Asset '{asset_id}' not found")
                )
            ast = ast_df.iloc[0]
            
            # Compatible parts
            parts_df = con.execute(
                "SELECT part_id, part_name, qty_on_hand, lead_time_days, unit_cost_inr FROM SPARE_PARTS WHERE compatible_asset_type = ? LIMIT 2",
                [ast["asset_type"]]
            ).df()

        parts = []
        for _, p in parts_df.iterrows():
            parts.append({
                "part_id": p["part_id"],
                "part_name": p["part_name"],
                "qty_needed": 1,
                "qty_on_hand": int(p["qty_on_hand"]),
                "lead_time_days": int(p["lead_time_days"]),
                "available": int(p["qty_on_hand"]) >= 1
            })

        cost_avoided = float(ast["downtime_cost_per_hr_inr"]) * 4.0
        now_utc = datetime.now(UTC)
        win_start = now_utc
        win_end = now_utc + timedelta(hours=int(al["predicted_window_hrs"]))

        draft = WorkOrderDraft(
            draft_id=f"DFT_{alert_id}",
            alert_id=alert_id,
            asset_id=asset_id,
            asset_name=ast["asset_name"],
            suspected_failure_mode=al["predicted_failure_mode"],
            recommended_action=f"Execute proactive diagnostic inspection for {al['predicted_failure_mode']}; replace component before unplanned breakdown.",
            parts=parts,
            proposed_window_start=win_start,
            proposed_window_end=win_end,
            estimated_labor_hours=3.5,
            estimated_cost_inr=5200.0,
            estimated_cost_avoided_inr=cost_avoided,
            risk_score_at_draft=float(al["risk_score"]),
            rationale=f"Model flagged high risk ({al['risk_score']:.2f}) with failure signature: {al['top_signals']}",
            created_ts=now_utc
        )
        return ServiceResult(
            ok=True,
            data=draft,
            meta=ServiceMeta(latency_ms=int((time.perf_counter() - start_t) * 1000))
        )
    except Exception as e:
        return ServiceResult(
            ok=False,
            error=ServiceError(code="QUERY_FAILED", message="Failed to generate work order draft", detail=str(e))
        )

# ─────────────────────────────────────────────────────────────
# 17. approve_work_order() (Idempotent - PRD 3 Section 4.4)
# ─────────────────────────────────────────────────────────────
def approve_work_order(
    draft: Union[WorkOrderDraft, Dict[str, Any]],
    approver: str,
    idempotency_key: Optional[str] = None
) -> ServiceResult[WorkOrderResult]:
    start_t = time.perf_counter()
    try:
        if not approver or not approver.strip():
            return ServiceResult(
                ok=False,
                error=ServiceError(code="VALIDATION_ERROR", message="Approver name is required for governance audit.")
            )

        draft_dict = draft if isinstance(draft, dict) else draft.__dict__
        
        # Build idempotency key if not passed
        if not idempotency_key:
            hash_src = f"{draft_dict.get('alert_id')}:{draft_dict.get('asset_id')}:{draft_dict.get('suspected_failure_mode')}"
            idempotency_key = f"{draft_dict.get('alert_id')}:{hashlib.md5(hash_src.encode()).hexdigest()[:12]}"

        result_dict, existed = local_duckdb.approve_work_order_db(
            draft_dict=draft_dict,
            approver=approver.strip(),
            idempotency_key=idempotency_key
        )

        res = WorkOrderResult(
            order_id=result_dict["order_id"],
            status=result_dict["status"],
            approved_by=result_dict["approved_by"],
            approved_ts=result_dict["approved_ts"],
            audit_id=result_dict["audit_id"],
            already_existed=existed
        )

        # Invalidate caches
        from app.services.cache import invalidate_caches
        invalidate_caches("work_order_approved")

        return ServiceResult(
            ok=True,
            data=res,
            meta=ServiceMeta(latency_ms=int((time.perf_counter() - start_t) * 1000))
        )
    except Exception as e:
        return ServiceResult(
            ok=False,
            error=ServiceError(code="QUERY_FAILED", message="Failed to approve work order", detail=str(e))
        )

# ─────────────────────────────────────────────────────────────
# 18. list_work_orders() (PRD 3 Section 4.2)
# ─────────────────────────────────────────────────────────────
def list_work_orders(source: Optional[str] = None, limit: int = 100) -> ServiceResult[pd.DataFrame]:
    return _wrap_call(local_duckdb.list_work_orders_data, source=source, limit=limit)
