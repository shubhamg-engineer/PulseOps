# FRONTEND_HANDOFF.md — PulseOps Frontend to Snowflake CoCo (Phase 2)

**Companion to:** PRD 1, PRD 2 (CoCo on Snowflake), and PRD 3 (Frontend UI Contract).  
**Target:** Autonomous CoCo Agent and engineers transitioning PulseOps from Local DuckDB to Snowflake Core + Cortex AI.

---

## 1. Architecture Summary

The PulseOps Command Center is built **contract-first** with strict isolation between the presentation tier (`app/pages/`) and data storage:

```
┌────────────────────────────────────── Streamlit UI ──────────────────────────────────────┐
│  app/streamlit_app.py (Shell, Replay Clock, Freshness, Outage Simulation)               │
│  app/pages/ (1_Fleet, 2_Alerts, 3_Drilldown, 4_AskAgent, 5_OEE_Impact, 6_WorkOrders)   │
│  app/components/ (KPI Cards, Status Chips, Plotly Telemetry, Risk Gauge, Modal Dialog)  │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │ calls
                                             ▼
┌────────────────────────────────────── services/api.py ───────────────────────────────────┐
│  The 18 Public Contract Methods (ServiceResult[T] envelope, timing, error codes)         │
│  app/services/contracts.py (Strict dataclass models, enums)                             │
│  app/services/normalize.py (Column lowercasing, UTC timestamps, top_signals JSON)       │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │ routes via BACKEND env
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
         BACKEND=local (DuckDB)                         BACKEND=snowflake (Cortex/Snowpark)
      app/data_access/local_duckdb.py                app/data_access/snowflake.py
```

### Critical Guarantee for Phase 2
**Zero Streamlit page code needs to be modified for Snowflake.**  
Only `app/data_access/snowflake.py` and the SQL queries it executes are touched in Phase 2.

---

## 2. Public Service Contract Methods & Snowflake Mapping

All 18 functions live in `app/services/api.py` and return `ServiceResult[T]`.

| # | Contract Function | Local DuckDB Implementation | Snowflake / Cortex Target Table / Function |
|---|---|---|---|
| 1 | `get_backend_info()` | Reads local config and dataset max TS | Checks connection to `PULSEOPS_PROD.CORE`, returns warehouse name |
| 2 | `get_data_freshness(as_of_ts)` | Queries `MAX(reading_ts)` from `SENSOR_READINGS` | `SELECT MAX(reading_ts) FROM PULSEOPS_PROD.CORE.SENSOR_READINGS` |
| 3 | `get_filters()` | `DISTINCT plant_id, line_id, asset_type` | `SELECT DISTINCT plant_id, line_id, asset_type FROM ASSETS` |
| 4 | `get_fleet_kpis(period_days, plant_id, as_of_ts)` | Aggregates `PRODUCTION_RUNS` & `ALERTS` | Dynamic SQL over `PRODUCTION_RUNS` & `ALERTS` |
| 5 | `get_asset_health(plant_id, as_of_ts)` | Joins `ASSETS`, `ALERTS`, `PRODUCTION_RUNS` | Joins `ASSETS` with latest model score table |
| 6 | `get_alerts(status, plant_id, min_risk, limit, as_of_ts)` | Queries `ALERTS` joined with `ASSETS` | `SELECT * FROM PULSEOPS_PROD.CORE.ALERTS ORDER BY priority_score DESC` |
| 7 | `update_alert_status(alert_id, status, actor)` | `UPDATE ALERTS SET status = ?` | `UPDATE PULSEOPS_PROD.CORE.ALERTS SET status = ?` |
| 8 | `get_asset_detail(asset_id, as_of_ts)` | Asset static + rolling risk + OEE | Asset metadata joined with Cortex telemetry features |
| 9 | `get_sensor_series(asset_id, start_ts, end_ts, resample, as_of_ts)` | Resamples 5-min readings to 15-min | Snowflake `TIME_SLICE(reading_ts, 15, 'MINUTE')` |
| 10 | `get_asset_orders(asset_id, limit)` | `SELECT FROM MAINTENANCE_ORDERS` | `SELECT FROM PULSEOPS_PROD.CORE.MAINTENANCE_ORDERS` |
| 11 | `get_spare_parts(asset_id)` | `SELECT FROM SPARE_PARTS` | `SELECT FROM PULSEOPS_PROD.CORE.SPARE_PARTS` |
| 12 | `get_related_docs(asset_id, failure_mode, limit)` | Keyword matching on `KNOWLEDGE_DOCS` | `SNOWFLAKE.CORTEX.SEARCH_PREVIEW` or vector search on docs |
| 13 | `get_oee_trend(group_by, period_days, granularity, as_of_ts)` | Date-grouped `PRODUCTION_RUNS` aggregates | Window functions over `PRODUCTION_RUNS` |
| 14 | `get_impact_summary(planned_fix_factor, as_of_ts)` | Replay calculation over `MAINTENANCE_ORDERS` | SQL stored procedure or analytical aggregate |
| 15 | `ask_agent(question, session_id, context, as_of_ts)` | Rule-based router + SQL generator + guardrails | **Cortex Analyst (Text-to-SQL)** + **Cortex Search (RAG)** |
| 16 | `draft_work_order(alert_id)` | Drafts `WorkOrderDraft` with parts lookup | Drafts order with parts and ROI estimation |
| 17 | `approve_work_order(draft, approver, idempotency_key)` | Idempotent `INSERT INTO MAINTENANCE_ORDERS` | Idempotent transaction `INSERT INTO MAINTENANCE_ORDERS` |
| 18 | `list_work_orders(source, limit)` | `SELECT FROM MAINTENANCE_ORDERS` | `SELECT FROM PULSEOPS_PROD.CORE.MAINTENANCE_ORDERS` |

---

## 3. Key Differences Between Backends & Normalization Rules

1. **Identifier Casing:**
   - DuckDB maintains case; Snowflake returns unquoted identifiers in `UPPERCASE`.
   - `app/services/normalize.py` automatically lowercases all columns to `snake_case`.
2. **JSON / VARIANT Types:**
   - In Snowflake, `top_signals` is stored as `VARIANT`.
   - `normalize.parse_top_signals()` handles Python `dict/list`, JSON strings, and raw text representations seamlessly.
3. **Idempotency Protection:**
   - Every work order approval passes an `idempotency_key = f"{alert_id}:{md5(draft_details)}"`.
   - The table `MAINTENANCE_ORDERS` includes `idempotency_key VARCHAR`. If re-submitted, it returns `already_existed=True` with no duplicate insertion.
4. **Time Travel / Replay Clock:**
   - When running against historical data, all queries filter on `WHERE reading_ts <= as_of_ts` and `created_ts <= as_of_ts`.

---

## 4. How to Run and Validate

### Local DuckDB (Phase 1 / PRD 3)
```bash
# Run full automated test suite (45 tests: unit + contract + AppTest UI)
pytest tests/ -v

# Launch interactive Command Center
streamlit run app/streamlit_app.py
```

### Snowflake (Phase 2 / PRD 2)
1. In `.env`:
   ```ini
   BACKEND=snowflake
   SNOWFLAKE_ACCOUNT=your_account
   SNOWFLAKE_USER=your_user
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_DATABASE=PULSEOPS_PROD
   SNOWFLAKE_SCHEMA=CORE
   SNOWFLAKE_WAREHOUSE=PULSEOPS_XS_WH
   ```
2. Run contract tests against Snowflake:
   ```bash
   pytest tests/contract/test_contract.py -v
   ```
3. Start Streamlit UI:
   ```bash
   streamlit run app/streamlit_app.py
   ```
