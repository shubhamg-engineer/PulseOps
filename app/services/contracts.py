from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")

# ─────────────────────────────────────────────────────────────
# Enums (PRD 3 Section 4.2)
# ─────────────────────────────────────────────────────────────
class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    AT_RISK = "AT_RISK"
    CRITICAL = "CRITICAL"

class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACK = "ACK"
    ACTIONED = "ACTIONED"
    DISMISSED = "DISMISSED"

class OrderType(str, Enum):
    PREVENTIVE = "PREVENTIVE"
    CORRECTIVE = "CORRECTIVE"
    EMERGENCY = "EMERGENCY"

class FailureMode(str, Enum):
    BEARING_WEAR = "BEARING_WEAR"
    MISALIGNMENT = "MISALIGNMENT"
    OVERHEATING = "OVERHEATING"
    MOTOR_WINDING = "MOTOR_WINDING"

# ─────────────────────────────────────────────────────────────
# Service Result Envelope (PRD 3 Section 4.1)
# ─────────────────────────────────────────────────────────────
@dataclass
class ServiceError:
    code: str  # BACKEND_UNAVAILABLE, QUERY_FAILED, NOT_FOUND, VALIDATION_ERROR, STALE_DATA, AGENT_ERROR, TIMEOUT, PERMISSION_DENIED
    message: str
    detail: Optional[str] = None

@dataclass
class ServiceMeta:
    backend: str = "local"
    latency_ms: int = 0
    cached: bool = False
    as_of_ts: Optional[datetime] = None

@dataclass
class ServiceResult(Generic[T]):
    ok: bool
    data: Optional[T] = None
    error: Optional[ServiceError] = None
    meta: ServiceMeta = field(default_factory=ServiceMeta)

# ─────────────────────────────────────────────────────────────
# Core Models (PRD 3 Section 4.2 - 4.4)
# ─────────────────────────────────────────────────────────────
@dataclass
class FleetKPIs:
    fleet_oee: float
    oee_delta_pp: float
    open_alerts: int
    critical_alerts: int
    assets_at_risk: int
    downtime_hours: float
    downtime_cost_inr: float
    failures_avoided: int
    period_days: int
    as_of_ts: datetime

@dataclass
class AssetDetail:
    asset: Dict[str, Any]
    current_risk_score: float
    health_status: str
    predicted_failure_mode: str
    predicted_window_start: Optional[datetime]
    predicted_window_end: Optional[datetime]
    confidence: str  # "high" | "medium" | "low"
    top_signals: List[Dict[str, Any]]
    why_flagged: str
    open_alert_id: Optional[str]
    oee_7d: float
    mtbf_hours: float
    mttr_hours: float
    last_reading_ts: Optional[datetime]

@dataclass
class ImpactSummary:
    downtime_avoided_hours: float
    oee_uplift_pp: float
    cost_saved_inr: float
    failures_total: int
    failures_caught: int
    median_lead_time_hours: float
    false_alarms_per_week: float
    assumptions: Dict[str, Any]

@dataclass
class AgentResponse:
    answer_markdown: str
    sources: List[Dict[str, Any]] = field(default_factory=list)  # {type: "document"|"table"|"metric", title: str, id: str}
    sql_used: List[str] = field(default_factory=list)
    confidence: str = "high"  # "high" | "medium" | "low"
    warnings: List[str] = field(default_factory=list)
    refused: bool = False
    refusal_reason: Optional[str] = None
    suggested_actions: List[Dict[str, Any]] = field(default_factory=list)
    follow_ups: List[str] = field(default_factory=list)
    latency_ms: int = 0

@dataclass
class WorkOrderDraft:
    draft_id: str
    alert_id: str
    asset_id: str
    asset_name: str
    suspected_failure_mode: str
    recommended_action: str
    parts: List[Dict[str, Any]]
    proposed_window_start: Optional[datetime]
    proposed_window_end: Optional[datetime]
    estimated_labor_hours: float
    estimated_cost_inr: float
    estimated_cost_avoided_inr: float
    risk_score_at_draft: float
    rationale: str
    created_ts: datetime

@dataclass
class WorkOrderResult:
    order_id: str
    status: str
    approved_by: str
    approved_ts: datetime
    audit_id: str
    already_existed: bool
