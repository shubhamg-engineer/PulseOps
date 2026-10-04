# Snowflake Deployment Runbook (PRD 2 Execution Guide)

## Deployment Execution Order

Follow these steps sequentially to deploy PulseOps into Snowflake:

| Step | Script / Artifact | Purpose | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **1** | [`00_setup.sql`](file:///e:/ishi/hack/New%20folder/snowflake/00_setup.sql) | Database, Schema, XS Warehouse (60s auto-suspend), Resource Monitor | Database `PULSEOPS_PROD`, Schema `CORE`, XS Warehouse created |
| **2** | [`01_stage_and_load.sql`](file:///e:/ishi/hack/New%20folder/snowflake/01_stage_and_load.sql) | Stages, DDL, and data loading | 7 tables created and loaded from `@PULSEOPS_STAGE` |
| **3** | [`02_features.sql`](file:///e:/ishi/hack/New%20folder/snowflake/02_features.sql) | Dynamic Table feature pipeline | `DT_SENSOR_FEATURES` initialized with 10-min lag |
| **4** | [`03_scoring.sql`](file:///e:/ishi/hack/New%20folder/snowflake/03_scoring.sql) | ML Scoring stored procedure | Stored procedure `GENERATE_PREDICTIVE_ALERTS` registered |
| **5** | [`04_semantic_view.yaml`](file:///e:/ishi/hack/New%20folder/snowflake/04_semantic_view.yaml) | Cortex Semantic View / Metric Layer | Semantic model deployed for natural-language analytics |
| **6** | [`05_search_service.sql`](file:///e:/ishi/hack/New%20folder/snowflake/05_search_service.sql) | Cortex Search Service | `PULSEOPS_DOC_SEARCH` service indexed over `KNOWLEDGE_DOCS` |
| **7** | [`06_agent_spec.md`](file:///e:/ishi/hack/New%20folder/snowflake/06_agent_spec.md) | Cortex Intelligence Agent | Agent registered with Semantic Model & Search tools |
| **8** | [`07_task.sql`](file:///e:/ishi/hack/New%20folder/snowflake/07_task.sql) | Automation task | Recurring 30-minute scoring task scheduled |
| **9** | [`08_streamlit_notes.md`](file:///e:/ishi/hack/New%20folder/snowflake/08_streamlit_notes.md) | Streamlit in Snowflake (SiS) App | Interactive command center live in Snowsight |

## Verification & Validation Checks
- Confirm row counts match [`golden_values.json`](file:///e:/ishi/hack/New%20folder/handoff/golden_values.json).
- Run the 15–20 question test suite in [`tests/agent_questions.yaml`](file:///e:/ishi/hack/New%20folder/tests/agent_questions.yaml).
- Ensure all items marked `-- VERIFY` are tested against your Snowflake account capabilities.
