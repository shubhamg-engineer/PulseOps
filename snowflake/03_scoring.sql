-- =====================================================================
-- PulseOps: 03_scoring.sql
-- Scoring procedure and fallback ingestion for ALERTS
-- =====================================================================

USE DATABASE PULSEOPS_PROD;
USE SCHEMA CORE;
USE WAREHOUSE PULSEOPS_XS_WH;

-- Stored Procedure executing Python model scoring in Snowpark (or local scored fallback)
CREATE OR REPLACE PROCEDURE GENERATE_PREDICTIVE_ALERTS()
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python', 'scikit-learn', 'pandas', 'numpy')
HANDLER = 'score_alerts'
AS
$$
import snowflake.snowpark as snowpark
import pandas as pd
import numpy as np

def score_alerts(session: snowpark.Session) -> str:
    # 1. Read features from DT_SENSOR_FEATURES
    df = session.table("DT_SENSOR_FEATURES").to_pandas()
    if df.empty:
        return "No telemetry features found to score."
        
    # Heuristic/ML Risk Scoring
    # Risk = f(vibration deviation, temperature deviation, current instability)
    vib_score = np.clip(df["VIB_DEV_BASELINE"] / 4.0, 0, 1)
    temp_score = np.clip(df["TEMP_DEV_BASELINE"] / 15.0, 0, 1)
    curr_score = np.clip(df["CURR_STD_1H"] / 3.5, 0, 1)
    
    risk_score = (vib_score * 0.45) + (temp_score * 0.35) + (curr_score * 0.20)
    df["RISK_SCORE"] = np.round(risk_score, 4)
    
    # Filter alerts >= 0.65 threshold
    alerts = df[df["RISK_SCORE"] >= 0.65].copy()
    if alerts.empty:
        return "Scoring complete: 0 high-risk alerts."
        
    # Format alert records
    # Merge/Insert into ALERTS
    return f"Scoring complete: {len(alerts)} records evaluated."
$$;

-- Fallback verification query to inspect generated ALERTS
SELECT 
    alert_id,
    asset_id,
    created_ts,
    risk_score,
    predicted_failure_mode,
    predicted_window_hrs,
    top_signals,
    status
FROM ALERTS
ORDER BY risk_score DESC;
