from typing import Optional
import duckdb
import numpy as np
import pandas as pd
from src.config import DUCKDB_PATH

def compute_rolling_features(con: Optional[duckdb.DuckDBPyConnection] = None) -> pd.DataFrame:
    """Compute rolling 1h, 6h, 24h statistical features and baseline deviations per asset."""
    if con is None:
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        
    print("Extracting sensor telemetry and computing rolling feature vectors in DuckDB...")
    
    # 5-min intervals: 1h = 12, 6h = 72, 24h = 288, 14d = 4032
    query = """
        WITH base_sensors AS (
            SELECT
                reading_ts,
                asset_id,
                vibration_mm_s,
                temperature_c,
                rpm,
                motor_current_a,
                -- 1h Rolling (12 rows)
                AVG(vibration_mm_s) OVER w_1h AS vib_mean_1h,
                MAX(vibration_mm_s) OVER w_1h AS vib_max_1h,
                STDDEV_POP(vibration_mm_s) OVER w_1h AS vib_std_1h,
                AVG(temperature_c) OVER w_1h AS temp_mean_1h,
                MAX(temperature_c) OVER w_1h AS temp_max_1h,
                AVG(motor_current_a) OVER w_1h AS curr_mean_1h,
                STDDEV_POP(motor_current_a) OVER w_1h AS curr_std_1h,
                
                -- 6h Rolling (72 rows)
                AVG(vibration_mm_s) OVER w_6h AS vib_mean_6h,
                MAX(vibration_mm_s) OVER w_6h AS vib_max_6h,
                AVG(temperature_c) OVER w_6h AS temp_mean_6h,
                MAX(temperature_c) OVER w_6h AS temp_max_6h,
                AVG(motor_current_a) OVER w_6h AS curr_mean_6h,
                
                -- 24h Rolling (288 rows)
                AVG(vibration_mm_s) OVER w_24h AS vib_mean_24h,
                AVG(temperature_c) OVER w_24h AS temp_mean_24h,
                AVG(motor_current_a) OVER w_24h AS curr_mean_24h,
                STDDEV_POP(rpm) OVER w_24h AS rpm_var_24h,
                
                -- 14-day baseline (4032 rows)
                AVG(vibration_mm_s) OVER w_14d AS vib_baseline_14d,
                AVG(temperature_c) OVER w_14d AS temp_baseline_14d,
                AVG(motor_current_a) OVER w_14d AS curr_baseline_14d
            FROM SENSOR_READINGS
            WINDOW
                w_1h AS (PARTITION BY asset_id ORDER BY reading_ts ROWS BETWEEN 11 PRECEDING AND CURRENT ROW),
                w_6h AS (PARTITION BY asset_id ORDER BY reading_ts ROWS BETWEEN 71 PRECEDING AND CURRENT ROW),
                w_24h AS (PARTITION BY asset_id ORDER BY reading_ts ROWS BETWEEN 287 PRECEDING AND CURRENT ROW),
                w_14d AS (PARTITION BY asset_id ORDER BY reading_ts ROWS BETWEEN 4031 PRECEDING AND CURRENT ROW)
        )
        SELECT
            b.*,
            -- Vibration slope (1h mean minus 6h mean)
            (b.vib_mean_1h - b.vib_mean_6h) AS vib_slope_6h,
            -- Deviations from 14-day baseline
            (b.vib_mean_1h - COALESCE(b.vib_baseline_14d, b.vib_mean_1h)) AS vib_dev_baseline,
            (b.temp_mean_1h - COALESCE(b.temp_baseline_14d, b.temp_mean_1h)) AS temp_dev_baseline,
            (b.curr_mean_1h - COALESCE(b.curr_baseline_14d, b.curr_mean_1h)) AS curr_dev_baseline,
            a.asset_type,
            a.criticality,
            a.rated_rpm
        FROM base_sensors b
        JOIN ASSETS a ON b.asset_id = a.asset_id
        ORDER BY b.asset_id, b.reading_ts
    """
    df_features = con.execute(query).df()
    print(f"Computed {len(df_features):,} feature rows.")
    return df_features
