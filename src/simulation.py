from typing import Any, Dict
import duckdb
import pandas as pd
from src.config import DUCKDB_PATH

def run_oee_impact_simulation(
    planned_fix_ratio: float = 0.40,
    con: Any = None
) -> Dict[str, Any]:
    """
    Replay 60-day historical data:
    Convert emergency breakdown downtime into shorter planned intervention windows (planned_fix_ratio = 40%).
    Compute baseline vs with-PulseOps metrics: downtime hours avoided, OEE uplift, and INR saved.
    """
    if con is None:
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        
    # Baseline totals
    query_base = """
        SELECT
            SUM(p.planned_minutes) AS total_planned_mins,
            SUM(p.run_minutes) AS baseline_run_mins,
            SUM(p.downtime_minutes) AS baseline_downtime_mins,
            SUM(p.ideal_units) AS total_ideal_units,
            SUM(p.actual_units) AS baseline_actual_units,
            SUM(p.good_units) AS baseline_good_units,
            SUM((p.downtime_minutes / 60.0) * a.downtime_cost_per_hr_inr) AS baseline_downtime_cost
        FROM PRODUCTION_RUNS p
        JOIN ASSETS a ON p.asset_id = a.asset_id
    """
    row_base = con.execute(query_base).fetchone()
    (
        total_planned_mins,
        base_run_mins,
        base_downtime_mins,
        total_ideal_units,
        base_actual_units,
        base_good_units,
        base_cost
    ) = row_base
    
    # Baseline OEE
    base_avail = base_run_mins / total_planned_mins
    base_perf = base_actual_units / total_ideal_units
    base_qual = base_good_units / base_actual_units
    base_oee = base_avail * base_perf * base_qual
    
    # Identify failures avoided by PulseOps
    # Injected emergency failures with lead time >= 24h
    fail_query = """
        SELECT 
            m.asset_id,
            m.labor_hours,
            m.cost_inr,
            a.downtime_cost_per_hr_inr,
            (m.labor_hours / 2.0) AS emergency_downtime_hours
        FROM MAINTENANCE_ORDERS m
        JOIN ASSETS a ON m.asset_id = a.asset_id
        WHERE m.order_type = 'EMERGENCY'
    """
    fails_df = con.execute(fail_query).df()
    
    # PulseOps converts 85% of emergency failures into planned maintenance
    avoided_count = int(len(fails_df) * 0.85)
    
    total_emergency_hours = fails_df["emergency_downtime_hours"].sum()
    hours_converted = fails_df.head(avoided_count)["emergency_downtime_hours"].sum()
    
    # Planned fix takes 40% (planned_fix_ratio) of emergency duration
    planned_fix_hours = hours_converted * planned_fix_ratio
    downtime_hours_saved = hours_converted - planned_fix_hours
    downtime_mins_saved = downtime_hours_saved * 60.0
    
    # With PulseOps
    opt_downtime_mins = base_downtime_mins - downtime_mins_saved
    opt_run_mins = base_run_mins + downtime_mins_saved
    
    # Units uplift
    units_per_min = base_actual_units / base_run_mins
    opt_actual_units = base_actual_units + (downtime_mins_saved * units_per_min)
    opt_good_units = base_good_units + (downtime_mins_saved * units_per_min * base_qual)
    
    opt_avail = opt_run_mins / total_planned_mins
    opt_perf = opt_actual_units / total_ideal_units
    opt_qual = opt_good_units / opt_actual_units
    opt_oee = opt_avail * opt_perf * opt_qual
    
    # Financial savings
    # Average downtime cost per hour across fleet
    avg_cost_per_hr = base_cost / (base_downtime_mins / 60.0) if base_downtime_mins > 0 else 12000.0
    inr_saved = downtime_hours_saved * avg_cost_per_hr
    opt_cost = base_cost - inr_saved
    
    return {
        "planned_fix_ratio": planned_fix_ratio,
        "failures_detected_early": avoided_count,
        "total_failures": len(fails_df),
        "downtime_hours_saved": round(downtime_hours_saved, 1),
        "inr_saved": round(inr_saved, 2),
        "baseline": {
            "oee": round(base_oee, 4),
            "availability": round(base_avail, 4),
            "performance": round(base_perf, 4),
            "quality": round(base_qual, 4),
            "downtime_hours": round(base_downtime_mins / 60.0, 1),
            "downtime_cost_inr": round(base_cost, 2)
        },
        "with_pulseops": {
            "oee": round(opt_oee, 4),
            "availability": round(opt_avail, 4),
            "performance": round(opt_perf, 4),
            "quality": round(opt_qual, 4),
            "downtime_hours": round(opt_downtime_mins / 60.0, 1),
            "downtime_cost_inr": round(opt_cost, 2)
        },
        "oee_uplift_pct_points": round((opt_oee - base_oee) * 100, 2),
        "downtime_reduction_pct": round((downtime_hours_saved / (base_downtime_mins / 60.0)) * 100, 1)
    }
