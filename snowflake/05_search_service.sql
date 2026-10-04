-- =====================================================================
-- PulseOps: 05_search_service.sql
-- Cortex Search Service definition over KNOWLEDGE_DOCS
-- =====================================================================

USE DATABASE PULSEOPS_PROD;
USE SCHEMA CORE;
USE WAREHOUSE PULSEOPS_XS_WH;

-- Create Cortex Search Service for RAG & technical document citations
CREATE OR REPLACE CORTEX SEARCH SERVICE PULSEOPS_DOC_SEARCH
    ON body
    ATTRIBUTES doc_id, title, asset_type, doc_type
    WAREHOUSE = PULSEOPS_XS_WH
    TARGET_LAG = '1 hour'
AS (
    SELECT
        doc_id,
        title,
        asset_type,
        doc_type,
        body
    FROM KNOWLEDGE_DOCS
);

-- Verification query testing Cortex Search (marked -- VERIFY for PRD 2 environment)
-- SELECT PARSE_JSON(
--     SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
--         'PULSEOPS_PROD.CORE.PULSEOPS_DOC_SEARCH',
--         '{ "query": "bearing vibration replacement SOP", "columns": ["doc_id", "title", "body"], "limit": 3 }'
--     )
-- )['results'] AS search_results; -- VERIFY
