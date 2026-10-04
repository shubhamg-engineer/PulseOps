from datetime import datetime
from typing import Any, Dict, Optional
import duckdb
import pandas as pd
from src.config import DUCKDB_PATH

def get_db_connection(con: Optional[duckdb.DuckDBPyConnection] = None) -> duckdb.DuckDBPyConnection:
    if con is not None:
        return con
    return duckdb.connect(str(DUCKDB_PATH), read_only=True)

def calculate_fleet_oee(con: Optional[duckdb.DuckDBPyConnection] = None) -> Dict[str, Any]:
    """Calculate overall fleet OEE, Availability, Performance, Quality, and totals."""
    conn = get_db_connection(con)
    query = """
        SELECT
            SUM(planned_minutes) AS total_planned_mins,
            SUM(run_minutes) AS total_run_mins,
            SUM(downtime_minutes) AS total_downtime_mins,
            SUM(ideal_units) AS total_ideal_units,
            SUM(actual_units) AS total_actual_units,
            SUM(good_units) AS total_good_units
        FROM PRODUCTION_RUNS
    """
    row = conn.execute(query).fetchone()
    if not row or row[0] is None or row[0] == 0:
        return {
            "availability": 0.0, "performance": 0.0, "quality": 0.0, "oee": 0.0,
            "total_planned_hours": 0.0, "total_run_hours": 0.0, "total_downtime_hours": 0.0
        }

    total_planned, total_run, total_downtime, total_ideal, total_actual, total_good = row
    
    availability = total_run / total_planned if total_planned > 0 else 0.0
    performance = total_actual / total_ideal if total_ideal > 0 else 0.0
    quality = total_good / total_actual if total_actual > 0 else 0.0
    oee = availability * performance * quality

    return {
        "availability": round(availability, 4),
        "performance": round(performance, 4),
        "quality": round(quality, 4),
        "oee": round(oee, 4),
        "total_planned_hours": round(total_planned / 60.0, 1),
        "total_run_hours": round(total_run / 60.0, 1),
        "total_downtime_hours": round(total_downtime / 60.0, 1),
        "total_actual_units": total_actual,
        "total_good_units": total_good
    }

def calculate_oee_by_plant(con: Optional[duckdb.DuckDBPyConnection] = None) -> pd.DataFrame:
    """Calculate OEE breakdown per plant."""
    conn = get_db_connection(con)
    query = """
        SELECT
            a.plant_id,
            SUM(p.planned_minutes) AS planned_mins,
            SUM(p.run_minutes) AS run_mins,
            SUM(p.downtime_minutes) AS downtime_mins,
            SUM(p.ideal_units) AS ideal_units,
            SUM(p.actual_units) AS actual_units,
            SUM(p.good_units) AS good_units,
            ROUND(SUM(p.run_minutes)::DOUBLE / NULLIF(SUM(p.planned_minutes), 0), 4) AS availability,
            ROUND(SUM(p.actual_units)::DOUBLE / NULLIF(SUM(p.ideal_units), 0), 4) AS performance,
            ROUND(SUM(p.good_units)::DOUBLE / NULLIF(SUM(p.actual_units), 0), 4) AS quality,
            ROUND(
                (SUM(p.run_minutes)::DOUBLE / NULLIF(SUM(p.planned_minutes), 0)) *
                (SUM(p.actual_units)::DOUBLE / NULLIF(SUM(p.ideal_units), 0)) *
                (SUM(p.good_units)::DOUBLE / NULLIF(SUM(p.actual_units), 0)), 4
            ) AS oee
        FROM PRODUCTION_RUNS p
        JOIN ASSETS a ON p.asset_id = a.asset_id
        GROUP BY a.plant_id
        ORDER BY a.plant_id
    """
    return conn.execute(query).df()

def calculate_oee_by_asset(con: Optional[duckdb.DuckDBPyConnection] = None) -> pd.DataFrame:
    """Calculate OEE breakdown per asset."""
    conn = get_db_connection(con)
    query = """
        SELECT
            a.asset_id,
            a.asset_name,
            a.plant_id,
            a.line_id,
            a.asset_type,
            a.criticality,
            a.downtime_cost_per_hr_inr,
            SUM(p.planned_minutes) / 60.0 AS planned_hours,
            SUM(p.run_minutes) / 60.0 AS run_hours,
            SUM(p.downtime_minutes) / 60.0 AS downtime_hours,
            ROUND(SUM(p.run_minutes)::DOUBLE / NULLIF(SUM(p.planned_minutes), 0), 4) AS availability,
            ROUND(SUM(p.actual_units)::DOUBLE / NULLIF(SUM(p.ideal_units), 0), 4) AS performance,
            ROUND(SUM(p.good_units)::DOUBLE / NULLIF(SUM(p.actual_units), 0), 4) AS quality,
            ROUND(
                (SUM(p.run_minutes)::DOUBLE / NULLIF(SUM(p.planned_minutes), 0)) *
                (SUM(p.actual_units)::DOUBLE / NULLIF(SUM(p.ideal_units), 0)) *
                (SUM(p.good_units)::DOUBLE / NULLIF(SUM(p.actual_units), 0)), 4
            ) AS oee,
            ROUND((SUM(p.downtime_minutes) / 60.0) * a.downtime_cost_per_hr_inr, 2) AS total_downtime_cost_inr
        FROM PRODUCTION_RUNS p
        JOIN ASSETS a ON p.asset_id = a.asset_id
        GROUP BY a.asset_id, a.asset_name, a.plant_id, a.line_id, a.asset_type, a.criticality, a.downtime_cost_per_hr_inr
        ORDER BY oee ASC
    """
    return conn.execute(query).df()

def calculate_mtbf_mttr(con: Optional[duckdb.DuckDBPyConnection] = None) -> Dict[str, Any]:
    """Calculate MTBF (operating hours / failures) and MTTR (mean repair duration in hours)."""
    conn = get_db_connection(con)
    
    # Total operating hours
    run_mins = conn.execute("SELECT SUM(run_minutes) FROM PRODUCTION_RUNS").fetchone()[0] or 0
    operating_hours = run_mins / 60.0
    
    # Emergency/Corrective failures
    fail_count = conn.execute("""
        SELECT COUNT(*) FROM MAINTENANCE_ORDERS 
        WHERE order_type IN ('EMERGENCY', 'CORRECTIVE')
    """).fetchone()[0] or 0
    
    # MTBF
    mtbf = operating_hours / fail_count if fail_count > 0 else 0.0
    
    # MTTR
    mttr_row = conn.execute("""
        SELECT 
            AVG(epoch(strptime(completed_ts, '%Y-%m-%d %H:%M:%S')) - epoch(strptime(created_ts, '%Y-%m-%d %H:%M:%S'))) / 3600.0 AS mttr_hours
        FROM MAINTENANCE_ORDERS
        WHERE order_type IN ('EMERGENCY', 'CORRECTIVE') AND completed_ts IS NOT NULL
    """).fetchone()
    
    mttr = mttr_row[0] if mttr_row and mttr_row[0] is not None else 0.0

    return {
        "operating_hours": round(operating_hours, 1),
        "total_failures": fail_count,
        "mtbf_hours": round(mtbf, 1),
        "mttr_hours": round(mttr, 2)
    }

def calculate_total_downtime_cost(con: Optional[duckdb.DuckDBPyConnection] = None) -> float:
    """Calculate fleet-wide downtime cost in INR."""
    conn = get_db_connection(con)
    query = """
        SELECT 
            SUM((p.downtime_minutes / 60.0) * a.downtime_cost_per_hr_inr) AS total_downtime_cost
        FROM PRODUCTION_RUNS p
        JOIN ASSETS a ON p.asset_id = a.asset_id
    """
    res = conn.execute(query).fetchone()[0]
    return round(float(res), 2) if res is not None else 0.0
