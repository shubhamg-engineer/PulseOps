-- =====================================================================
-- PulseOps: 01_stage_and_load.sql
-- Stages, File Formats, Table Schemas, and COPY INTO pipelines
-- =====================================================================

USE DATABASE PULSEOPS_PROD;
USE SCHEMA CORE;
USE WAREHOUSE PULSEOPS_XS_WH;

-- 1. File Formats
CREATE OR REPLACE FILE FORMAT CSV_FORMAT
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    RECORD_DELIMITER = '\n'
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('', 'NULL', 'None');

CREATE OR REPLACE FILE FORMAT PARQUET_FORMAT
    TYPE = 'PARQUET';

-- 2. Internal Staging Area
CREATE OR REPLACE STAGE PULSEOPS_STAGE
    FILE_FORMAT = CSV_FORMAT
    DIRECTORY = (ENABLE = TRUE);

-- 3. Target DDL Tables
CREATE OR REPLACE TABLE ASSETS (
    asset_id VARCHAR(50) PRIMARY KEY,
    asset_name VARCHAR(100),
    plant_id VARCHAR(50),
    line_id VARCHAR(50),
    asset_type VARCHAR(50),
    criticality INT,
    install_date DATE,
    rated_rpm INT,
    ideal_cycle_time_sec INT,
    downtime_cost_per_hr_inr FLOAT
);

CREATE OR REPLACE TABLE SPARE_PARTS (
    part_id VARCHAR(50) PRIMARY KEY,
    part_name VARCHAR(100),
    compatible_asset_type VARCHAR(50),
    qty_on_hand INT,
    lead_time_days INT,
    unit_cost_inr FLOAT
);

CREATE OR REPLACE TABLE KNOWLEDGE_DOCS (
    doc_id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200),
    asset_type VARCHAR(50),
    doc_type VARCHAR(50),
    body TEXT
);

CREATE OR REPLACE TABLE SENSOR_READINGS (
    reading_ts TIMESTAMP_NTZ,
    asset_id VARCHAR(50),
    vibration_mm_s FLOAT,
    temperature_c FLOAT,
    rpm FLOAT,
    motor_current_a FLOAT
);

CREATE OR REPLACE TABLE MAINTENANCE_ORDERS (
    order_id VARCHAR(50) PRIMARY KEY,
    asset_id VARCHAR(50),
    order_type VARCHAR(50),
    source VARCHAR(50),
    status VARCHAR(50),
    created_ts TIMESTAMP_NTZ,
    completed_ts TIMESTAMP_NTZ,
    failure_mode VARCHAR(100),
    parts_used VARCHAR(100),
    labor_hours FLOAT,
    cost_inr FLOAT,
    technician_notes TEXT
);

CREATE OR REPLACE TABLE PRODUCTION_RUNS (
    run_id VARCHAR(50) PRIMARY KEY,
    asset_id VARCHAR(50),
    shift_date DATE,
    shift VARCHAR(10),
    planned_minutes INT,
    run_minutes INT,
    downtime_minutes INT,
    ideal_units INT,
    actual_units INT,
    good_units INT
);

CREATE OR REPLACE TABLE ALERTS (
    alert_id VARCHAR(50) PRIMARY KEY,
    asset_id VARCHAR(50),
    created_ts TIMESTAMP_NTZ,
    risk_score FLOAT,
    predicted_failure_mode VARCHAR(100),
    predicted_window_hrs INT,
    top_signals TEXT,
    status VARCHAR(50)
);

-- 4. COPY INTO Commands (Staged files from /data)
-- PUT file://data/assets.csv @PULSEOPS_STAGE/
COPY INTO ASSETS FROM @PULSEOPS_STAGE/assets.csv FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);
COPY INTO SPARE_PARTS FROM @PULSEOPS_STAGE/spare_parts.csv FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);
COPY INTO KNOWLEDGE_DOCS FROM @PULSEOPS_STAGE/knowledge_docs.csv FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);
COPY INTO SENSOR_READINGS FROM @PULSEOPS_STAGE/sensor_readings.csv FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);
COPY INTO MAINTENANCE_ORDERS FROM @PULSEOPS_STAGE/maintenance_orders.csv FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);
COPY INTO PRODUCTION_RUNS FROM @PULSEOPS_STAGE/production_runs.csv FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);
COPY INTO ALERTS FROM @PULSEOPS_STAGE/alerts.csv FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);
