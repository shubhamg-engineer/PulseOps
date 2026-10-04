from datetime import datetime, timedelta, timezone
import pytest
import pandas as pd

from app.services import api
from app.services.contracts import (
    AgentResponse,
    AssetDetail,
    FleetKPIs,
    ImpactSummary,
    ServiceResult,
    WorkOrderDraft,
    WorkOrderResult
)

UTC = timezone.utc

def test_get_backend_info():
    res = api.get_backend_info()
    assert isinstance(res, ServiceResult)
    assert res.ok is True
    assert res.data is not None
    assert "backend" in res.data
    assert "warehouse" in res.data

def test_get_data_freshness():
    res = api.get_data_freshness()
    assert isinstance(res, ServiceResult)
    assert res.ok is True
    assert "latest_reading_ts" in res.data
    assert "is_stale" in res.data
    assert isinstance(res.data["is_stale"], bool)

def test_get_filters():
    res = api.get_filters()
    assert isinstance(res, ServiceResult)
    assert res.ok is True
    assert "plants" in res.data
    assert len(res.data["plants"]) >= 3
    assert "lines" in res.data
    assert "asset_types" in res.data

def test_get_fleet_kpis():
    res = api.get_fleet_kpis(period_days=7)
    assert isinstance(res, ServiceResult)
    assert res.ok is True
    assert isinstance(res.data, FleetKPIs)
    assert 0.0 < res.data.fleet_oee <= 1.0
    assert res.data.open_alerts >= 0
    assert res.data.downtime_hours >= 0

def test_get_asset_health():
    res = api.get_asset_health()
    assert isinstance(res, ServiceResult)
    assert res.ok is True
    assert isinstance(res.data, pd.DataFrame)
    required_cols = [
        "asset_id", "asset_name", "plant_id", "line_id", "asset_type",
        "criticality", "risk_score", "health_status", "oee_7d",
        "last_reading_ts", "open_alerts"
    ]
    for col in required_cols:
        assert col in res.data.columns, f"Missing column {col} in asset health"
    assert len(res.data) == 25

def test_get_alerts():
    res = api.get_alerts()
    assert isinstance(res, ServiceResult)
    assert res.ok is True
    assert isinstance(res.data, pd.DataFrame)
    required_cols = [
        "alert_id", "asset_id", "asset_name", "plant_id", "line_id",
        "asset_type", "criticality", "created_ts", "risk_score",
        "health_status", "priority_score", "predicted_failure_mode",
        "predicted_window_hrs", "top_signals", "status", "downtime_cost_per_hr_inr"
    ]
    for col in required_cols:
        assert col in res.data.columns, f"Missing column {col} in alerts"
    if not res.data.empty:
        # Check priority_score descending order
        scores = res.data["priority_score"].tolist()
        assert scores == sorted(scores, reverse=True)

def test_update_alert_status():
    alerts_res = api.get_alerts()
    assert not alerts_res.data.empty
    test_id = alerts_res.data.iloc[0]["alert_id"]
    
    # Valid update
    update_res = api.update_alert_status(test_id, "ACK", actor="tester")
    assert update_res.ok is True
    assert update_res.data["status"] == "ACK"
    
    # Invalid status -> validation error
    bad_res = api.update_alert_status(test_id, "INVALID_STATUS")
    assert bad_res.ok is False
    assert bad_res.error.code == "VALIDATION_ERROR"
    
    # Reset back to OPEN
    api.update_alert_status(test_id, "OPEN", actor="tester")

def test_get_asset_detail_and_not_found():
    # Valid asset
    res = api.get_asset_detail("AST_101")
    assert res.ok is True
    assert isinstance(res.data, AssetDetail)
    assert res.data.asset["asset_id"] == "AST_101"
    assert res.data.health_status in ["HEALTHY", "WATCH", "AT_RISK", "CRITICAL"]

    # Unknown asset -> NOT_FOUND
    res_bad = api.get_asset_detail("AST_9999")
    assert res_bad.ok is False
    assert res_bad.error.code == "NOT_FOUND"

def test_get_sensor_series():
    res = api.get_sensor_series("AST_101")
    assert res.ok is True
    assert isinstance(res.data, pd.DataFrame)
    required_cols = ["ts", "vibration_mm_s", "temperature_c", "rpm", "motor_current_a", "risk_score"]
    for col in required_cols:
        assert col in res.data.columns

def test_get_asset_orders():
    res = api.get_asset_orders("AST_101", limit=5)
    assert res.ok is True
    assert isinstance(res.data, pd.DataFrame)
    for col in ["order_id", "order_type", "status", "cost_inr"]:
        assert col in res.data.columns

def test_get_spare_parts():
    res = api.get_spare_parts("AST_101")
    assert res.ok is True
    assert isinstance(res.data, pd.DataFrame)
    for col in ["part_id", "part_name", "qty_on_hand", "lead_time_days", "unit_cost_inr"]:
        assert col in res.data.columns

def test_get_related_docs():
    res = api.get_related_docs(asset_id="AST_101", limit=3)
    assert res.ok is True
    assert isinstance(res.data, pd.DataFrame)
    for col in ["doc_id", "title", "doc_type", "snippet"]:
        assert col in res.data.columns

def test_get_oee_trend():
    res = api.get_oee_trend(group_by="plant", period_days=14)
    assert res.ok is True
    assert isinstance(res.data, pd.DataFrame)
    for col in ["period_start", "group_id", "group_name", "availability", "performance", "quality", "oee"]:
        assert col in res.data.columns

def test_get_impact_summary():
    res = api.get_impact_summary(planned_fix_factor=0.40)
    assert res.ok is True
    summary, events = res.data
    assert isinstance(summary, ImpactSummary)
    assert summary.cost_saved_inr > 0
    assert summary.downtime_avoided_hours > 0
    assert isinstance(events, pd.DataFrame)

def test_ask_agent():
    # Regular question
    res = api.ask_agent("What is the overall fleet OEE?")
    assert res.ok is True
    assert isinstance(res.data, AgentResponse)
    assert len(res.data.answer_markdown) > 0
    assert res.data.refused is False
    assert len(res.data.sources) > 0

    # Guardrail out of scope rejection
    res_oos = api.ask_agent("What is the bitcoin price in USD?")
    assert res_oos.ok is True
    assert res_oos.data.refused is True
    assert res_oos.data.refusal_reason is not None

def test_draft_and_approve_work_order_idempotent():
    alerts = api.get_alerts()
    assert not alerts.data.empty
    alt_id = alerts.data.iloc[0]["alert_id"]
    
    # 1. Draft
    draft_res = api.draft_work_order(alt_id)
    assert draft_res.ok is True
    assert isinstance(draft_res.data, WorkOrderDraft)
    assert draft_res.data.alert_id == alt_id
    
    # 2. Approve first time
    idemp_key = f"TEST_IDEMP_{alt_id}_{int(datetime.now().timestamp())}"
    app_res1 = api.approve_work_order(draft_res.data, approver="P. Sharma", idempotency_key=idemp_key)
    assert app_res1.ok is True
    assert isinstance(app_res1.data, WorkOrderResult)
    assert app_res1.data.already_existed is False
    assert app_res1.data.status == "SCHEDULED"
    
    # 3. Approve second time with same idempotency key -> already_existed is True
    app_res2 = api.approve_work_order(draft_res.data, approver="P. Sharma", idempotency_key=idemp_key)
    assert app_res2.ok is True
    assert app_res2.data.already_existed is True
    assert app_res2.data.order_id == app_res1.data.order_id

def test_list_work_orders():
    res = api.list_work_orders(limit=10)
    assert res.ok is True
    assert isinstance(res.data, pd.DataFrame)
    required_cols = [
        "order_id", "asset_id", "order_type", "source", "status",
        "created_ts", "approved_by", "approved_ts", "risk_score_at_draft",
        "estimated_cost_avoided_inr"
    ]
    for col in required_cols:
        assert col in res.data.columns
