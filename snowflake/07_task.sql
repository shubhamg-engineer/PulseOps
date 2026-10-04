-- =====================================================================
-- PulseOps: 07_task.sql
-- Scheduled Task for automated model scoring & feature refresh
-- =====================================================================

USE DATABASE PULSEOPS_PROD;
USE SCHEMA CORE;
USE WAREHOUSE PULSEOPS_XS_WH;

-- Create scheduled task executing every 30 minutes
CREATE OR REPLACE TASK PULSEOPS_PERIODIC_SCORING_TASK
    WAREHOUSE = PULSEOPS_XS_WH
    SCHEDULE = '30 MINUTE'
AS
    CALL GENERATE_PREDICTIVE_ALERTS();

-- To activate task in production (uncomment during PRD 2 deployment):
-- ALTER TASK PULSEOPS_PERIODIC_SCORING_TASK RESUME; -- VERIFY
