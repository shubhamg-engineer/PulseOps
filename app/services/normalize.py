import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

DISPLAY_TZ = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc

def to_snake_case(s: str) -> str:
    """Normalize string or column name to lowercase snake_case."""
    s = re.sub(r"[\s\-]+", "_", s.strip())
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower()

def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all DataFrame columns are lowercase snake_case."""
    df = df.copy()
    df.columns = [to_snake_case(c) for c in df.columns]
    return df

def to_utc_datetime(val: Any) -> Optional[datetime]:
    """Convert any timestamp/string/epoch to a timezone-aware UTC datetime."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=UTC)
        return val.astimezone(UTC)
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=UTC)
    # Parse string
    try:
        dt = pd.to_datetime(val)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None

def format_display_time(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M IST") -> str:
    """Format UTC datetime for display in Asia/Kolkata timezone."""
    if dt is None:
        return "N/A"
    utc_dt = to_utc_datetime(dt)
    if not utc_dt:
        return "N/A"
    local_dt = utc_dt.astimezone(DISPLAY_TZ)
    return local_dt.strftime(fmt)

def normalize_scalar(val: Any) -> Any:
    """Convert numpy scalars or Decimal to native Python types."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    if pd.isna(val):
        return None
    return val

def risk_to_health_status(risk_score: float) -> str:
    """Map numeric risk score to PRD 3 health status string."""
    score = float(risk_score) if risk_score is not None else 0.0
    if score < 0.30:
        return "HEALTHY"
    elif score < 0.60:
        return "WATCH"
    elif score < 0.80:
        return "AT_RISK"
    else:
        return "CRITICAL"

def parse_top_signals(signals_raw: Any) -> List[Dict[str, Any]]:
    """
    Parse top_signals into a list of dicts:
    [{'signal': 'Vibration', 'direction': '+', 'contribution': 0.45}, ...]
    Handles raw JSON, Snowflake variant string, or legacy plain text string.
    """
    if not signals_raw or pd.isna(signals_raw):
        return []
    
    if isinstance(signals_raw, list):
        return signals_raw
        
    if isinstance(signals_raw, str):
        # Try JSON parse first
        signals_str = signals_raw.strip()
        if signals_str.startswith("[") or signals_str.startswith("{"):
            try:
                parsed = json.loads(signals_str)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict):
                    return [parsed]
            except Exception:
                pass
                
        # Parse legacy plain text like:
        # "Vibration +4.6 mm/s over baseline, slope 0.34" or "Current instability std=0.3A"
        results = []
        parts = [p.strip() for p in signals_str.split(",") if p.strip()]
        for p in parts:
            direction = "+" if "+" in p or "elevated" in p.lower() or "high" in p.lower() else "-"
            # Extract signal name
            sig_name = "Signal"
            for candidate in ["vibration", "temperature", "rpm", "motor_current", "current", "pressure"]:
                if candidate in p.lower():
                    sig_name = candidate.title()
                    break
            results.append({
                "signal": p,
                "direction": direction,
                "contribution": 0.50
            })
        return results if results else [{"signal": signals_str, "direction": "+", "contribution": 0.50}]

    return []

def calculate_priority_score(
    risk_score: float,
    criticality: int,
    downtime_cost_per_hr_inr: float,
    max_downtime_cost_per_hr_inr: float = 25000.0
) -> float:
    """
    Priority score = risk_score * (criticality / 5.0) * (downtime_cost_per_hr_inr / max_cost) * 100.0
    """
    r = float(risk_score or 0.0)
    c = float(criticality or 1.0) / 5.0
    max_cost = max(float(max_downtime_cost_per_hr_inr or 25000.0), 1000.0)
    cost_ratio = float(downtime_cost_per_hr_inr or 0.0) / max_cost
    return round(r * c * cost_ratio * 100.0, 2)
