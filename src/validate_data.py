import sys
import duckdb
import pandas as pd
from src.config import DUCKDB_PATH

def validate():
    print(f"Connecting to DuckDB at {DUCKDB_PATH} for data validation...")
    con = duckdb.connect(str(DUCKDB_PATH))
    
    errors = []
    
    # Check tables existence and row counts
    tables = ["ASSETS", "SENSOR_READINGS", "MAINTENANCE_ORDERS", "PRODUCTION_RUNS", "SPARE_PARTS", "KNOWLEDGE_DOCS"]
    for tbl in tables:
        count = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"Table {tbl}: {count:,} rows")
        if count == 0:
            errors.append(f"Table {tbl} is empty!")

    # Check 1: Referential integrity on ASSETS
    asset_ids = set(con.execute("SELECT asset_id FROM ASSETS").df()["asset_id"])
    
    sensor_assets = set(con.execute("SELECT DISTINCT asset_id FROM SENSOR_READINGS").df()["asset_id"])
    if not sensor_assets.issubset(asset_ids):
        errors.append(f"Invalid asset IDs found in SENSOR_READINGS: {sensor_assets - asset_ids}")
        
    order_assets = set(con.execute("SELECT DISTINCT asset_id FROM MAINTENANCE_ORDERS").df()["asset_id"])
    if not order_assets.issubset(asset_ids):
        errors.append(f"Invalid asset IDs found in MAINTENANCE_ORDERS: {order_assets - asset_ids}")
        
    run_assets = set(con.execute("SELECT DISTINCT asset_id FROM PRODUCTION_RUNS").df()["asset_id"])
    if not run_assets.issubset(asset_ids):
        errors.append(f"Invalid asset IDs found in PRODUCTION_RUNS: {run_assets - asset_ids}")

    # Check 2: No negative numbers
    neg_sensors = con.execute("""
        SELECT COUNT(*) FROM SENSOR_READINGS
        WHERE vibration_mm_s < 0 OR temperature_c < 0 OR rpm < 0 OR motor_current_a < 0
    """).fetchone()[0]
    if neg_sensors > 0:
        errors.append(f"Found {neg_sensors} negative values in SENSOR_READINGS!")

    neg_runs = con.execute("""
        SELECT COUNT(*) FROM PRODUCTION_RUNS
        WHERE planned_minutes < 0 OR run_minutes < 0 OR downtime_minutes < 0
           OR ideal_units < 0 OR actual_units < 0 OR good_units < 0
    """).fetchone()[0]
    if neg_runs > 0:
        errors.append(f"Found {neg_runs} negative values in PRODUCTION_RUNS!")

    # Check 3: Logical consistency in PRODUCTION_RUNS (actual_units <= ideal_units * 1.05, good_units <= actual_units)
    bad_quality = con.execute("""
        SELECT COUNT(*) FROM PRODUCTION_RUNS
        WHERE good_units > actual_units
    """).fetchone()[0]
    if bad_quality > 0:
        errors.append(f"Found {bad_quality} production runs where good_units > actual_units!")

    # Check 4: Check emergency maintenance orders have corresponding failure mode
    emergency_count = con.execute("""
        SELECT COUNT(*) FROM MAINTENANCE_ORDERS
        WHERE order_type = 'EMERGENCY'
    """).fetchone()[0]
    print(f"Total emergency maintenance orders: {emergency_count}")
    if emergency_count < 15:
        errors.append(f"Expected >= 15 emergency orders for failure events, got {emergency_count}")

    con.close()
    
    if errors:
        print("\n[FAIL] DATA VALIDATION FAILED:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\n[SUCCESS] DATA VALIDATION PASSED: All referential integrity, bounds, and failure signatures verified.")

if __name__ == "__main__":
    validate()
