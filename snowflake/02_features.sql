-- =====================================================================
-- PulseOps: 02_features.sql
-- Feature Layer as Snowflake Dynamic Tables (Mirrors F1 Feature Engineering)
-- =====================================================================

USE DATABASE PULSEOPS_PROD;
USE SCHEMA CORE;
USE WAREHOUSE PULSEOPS_XS_WH;

-- Dynamic Table computing rolling 1h, 6h, 24h features with 10-minute lag
CREATE OR REPLACE DYNAMIC TABLE DT_SENSOR_FEATURES
    TARGET_LAG = '10 MINUTES'
    WAREHOUSE = PULSEOPS_XS_WH
AS
WITH base_sensors AS (
    SELECT
        reading_ts,
        asset_id,
        vibration_mm_s,
        temperature_c,
        rpm,
        motor_current_a,
        
        -- 1-Hour Rolling Stats (12 intervals)
        AVG(vibration_mm_s) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS vib_mean_1h,
        MAX(vibration_mm_s) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS vib_max_1h,
        STDDEV(vibration_mm_s) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS vib_std_1h,
        AVG(temperature_c) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS temp_mean_1h,
        MAX(temperature_c) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS temp_max_1h,
        AVG(motor_current_a) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS curr_mean_1h,
        STDDEV(motor_current_a) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS curr_std_1h,
        
        -- 6-Hour Rolling Stats (72 intervals)
        AVG(vibration_mm_s) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 71 PRECEDING AND CURRENT ROW
        ) AS vib_mean_6h,
        MAX(vibration_mm_s) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 71 PRECEDING AND CURRENT ROW
        ) AS vib_max_6h,
        AVG(temperature_c) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 71 PRECEDING AND CURRENT ROW
        ) AS temp_mean_6h,
        MAX(temperature_c) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 71 PRECEDING AND CURRENT ROW
        ) AS temp_max_6h,
        AVG(motor_current_a) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 71 PRECEDING AND CURRENT ROW
        ) AS curr_mean_6h,
        
        -- 24-Hour Rolling Stats (288 intervals)
        AVG(vibration_mm_s) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 287 PRECEDING AND CURRENT ROW
        ) AS vib_mean_24h,
        AVG(temperature_c) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 287 PRECEDING AND CURRENT ROW
        ) AS temp_mean_24h,
        AVG(motor_current_a) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 287 PRECEDING AND CURRENT ROW
        ) AS curr_mean_24h,
        STDDEV(rpm) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 287 PRECEDING AND CURRENT ROW
        ) AS rpm_var_24h,
        
        -- 14-Day Baseline Reference (4032 intervals)
        AVG(vibration_mm_s) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 4031 PRECEDING AND CURRENT ROW
        ) AS vib_baseline_14d,
        AVG(temperature_c) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 4031 PRECEDING AND CURRENT ROW
        ) AS temp_baseline_14d,
        AVG(motor_current_a) OVER (
            PARTITION BY asset_id ORDER BY reading_ts 
            ROWS BETWEEN 4031 PRECEDING AND CURRENT ROW
        ) AS curr_baseline_14d
    FROM SENSOR_READINGS
)
SELECT
    b.reading_ts,
    b.asset_id,
    a.plant_id,
    a.line_id,
    a.asset_type,
    a.criticality,
    a.rated_rpm,
    b.vibration_mm_s,
    b.temperature_c,
    b.rpm,
    b.motor_current_a,
    b.vib_mean_1h,
    b.vib_max_1h,
    b.vib_std_1h,
    b.temp_mean_1h,
    b.temp_max_1h,
    b.curr_mean_1h,
    b.curr_std_1h,
    b.vib_mean_6h,
    b.vib_max_6h,
    b.temp_mean_6h,
    b.temp_max_6h,
    b.curr_mean_6h,
    b.vib_mean_24h,
    b.temp_mean_24h,
    b.curr_mean_24h,
    b.rpm_var_24h,
    (b.vib_mean_1h - b.vib_mean_6h) AS vib_slope_6h,
    (b.vib_mean_1h - COALESCE(b.vib_baseline_14d, b.vib_mean_1h)) AS vib_dev_baseline,
    (b.temp_mean_1h - COALESCE(b.temp_baseline_14d, b.temp_mean_1h)) AS temp_dev_baseline,
    (b.curr_mean_1h - COALESCE(b.curr_baseline_14d, b.curr_mean_1h)) AS curr_dev_baseline
FROM base_sensors b
JOIN ASSETS a ON b.asset_id = a.asset_id;
