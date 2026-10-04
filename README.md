# PulseOps — Predictive Maintenance & OEE Command Center

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/Database-DuckDB%20%7C%20Snowflake-yellow.svg)](https://duckdb.org/)
[![Streamlit](https://img.shields.io/badge/UI-Multipage%20Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Contract Tests](https://img.shields.io/badge/Contract%20Tests-17%20Passed-brightgreen.svg)]()
[![Full Test Suite](https://img.shields.io/badge/Tests-45%20Passed-brightgreen.svg)]()

> **Snowflake CoCo CLI Hackathon (GCC Edition)**  
> **Problem Statement:** Predictive Maintenance and OEE Command Center  
> **Phase 1 & PRD 3 Deliverable:** Complete, local-first production build with DuckDB, Scikit-Learn, 6-page contract-first Streamlit UI, time-travel replay clock, and full Snowflake deployment pack.

---

## 🚀 Quick Start (One Command)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate data & validate integrity
make data

# 3. Train predictive ML model & score alerts
make train

# 4. Run automated test suite (45 unit, contract, Q&A, and AppTest UI tests)
make test

# 5. Launch Multipage Streamlit Command Center
make run
```

---

## 🏭 Problem Statement & Solution

Manufacturers suffer costly unplanned downtime because **OT sensor telemetry** (vibration, temperature, RPM, current) operates in silos apart from **ERP maintenance records** (work orders, spare parts, production schedules).

**PulseOps** bridges both domains into an actionable intelligence command center:
1. **Fleet Health Heatmap:** Real-time visibility into 25 assets across 3 plants and 5 manufacturing lines.
2. **Predictive Alert Queue:** Ranked by `Risk Score × Criticality × Downtime Cost Rate` with ≥ 24h median lead time.
3. **Multi-Sensor Physics Telemetry:** 72-hour physical signature drill-down with shaded failure prediction windows.
4. **Root-Cause AI Agent:** Natural-language SQL analytics over metric layer + cited SOP/Tech-Note retrieval.
5. **Human-in-the-Loop Work Order Flow:** AI drafts work order with spare parts allocation -> Human approves -> Persisted to `MAINTENANCE_ORDERS`.
6. **OEE Impact Simulation:** 60-day historical replay converting emergency stops to scheduled 40% duration fixes, measuring downtime hours avoided, OEE uplift, and financial ROI.

---

## 📊 Benchmark Metrics & Golden Values

Refer to [`handoff/golden_values.json`](file:///e:/ishi/hack/New%20folder/handoff/golden_values.json):

| Metric | Measured Value | Standard / Formula |
| :--- | :--- | :--- |
| **Fleet OEE** | **~90.8%** | Availability × Performance × Quality |
| **Availability** | **98.7%** | Run Minutes / Planned Minutes |
| **Performance** | **94.2%** | Actual Units / Ideal Units |
| **Quality** | **97.7%** | Good Units / Actual Units |
| **Telemetry Rows** | **432,000 rows** | 25 assets × 60 days × 5-min intervals |
| **Emergency Failures** | **22 events** | Seeded with realistic degradation physics |
| **Model Median Lead Time** | **63.8 Hours** | Exceeds requirement (≥ 24.0h) |

---

## ❄️ Snowflake Deployment Pack (`/snowflake`)

Designed for **PRD 2 (Snowflake CoCo)** to deploy with zero modification:
- [`00_setup.sql`](file:///e:/ishi/hack/New%20folder/snowflake/00_setup.sql): Database `PULSEOPS_PROD`, Schema `CORE`, XS Warehouse with 60s auto-suspend, Resource Monitor with credit cap.
- [`01_stage_and_load.sql`](file:///e:/ishi/hack/New%20folder/snowflake/01_stage_and_load.sql): Table DDLs, file formats, and `COPY INTO` pipeline for all 7 entities.
- [`02_features.sql`](file:///e:/ishi/hack/New%20folder/snowflake/02_features.sql): Dynamic Table `DT_SENSOR_FEATURES` computing rolling 1h, 6h, 24h features.
- [`03_scoring.sql`](file:///e:/ishi/hack/New%20folder/snowflake/03_scoring.sql): Stored procedure `GENERATE_PREDICTIVE_ALERTS` executing predictive scoring.
- [`04_semantic_view.yaml`](file:///e:/ishi/hack/New%20folder/snowflake/04_semantic_view.yaml): Semantic Model for Snowflake Cortex Analyst.
- [`05_search_service.sql`](file:///e:/ishi/hack/New%20folder/snowflake/05_search_service.sql): Cortex Search Service over `KNOWLEDGE_DOCS`.
- [`06_agent_spec.md`](file:///e:/ishi/hack/New%20folder/snowflake/06_agent_spec.md): Cortex Intelligence Agent instructions and guardrails.
- [`07_task.sql`](file:///e:/ishi/hack/New%20folder/snowflake/07_task.sql): Recurring 30-minute automated scoring task.
- [`08_streamlit_notes.md`](file:///e:/ishi/hack/New%20folder/snowflake/08_streamlit_notes.md): Streamlit in Snowflake (SiS) configuration.
- [`DEPLOY.md`](file:///e:/ishi/hack/New%20folder/snowflake/DEPLOY.md): Complete deployment sequence and verification runbook.

---

## 🧪 Testing Suite

Run full automated tests:
```bash
pytest -v tests/
```
- `tests/test_metrics.py`: Verifies mathematical integrity of OEE, Availability, Performance, Quality, MTBF, MTTR, and Cost.
- `tests/test_agent.py`: Executes 16 test questions from `tests/agent_questions.yaml`, testing SQL queries, SOP citations, out-of-scope refusals, and work order creation.
- `tests/contract/test_contract.py`: 17 contract tests covering all `services/api.py` endpoints, input validation, schemas, and work order approval idempotency.
- `tests/ui/test_ui.py`: Streamlit `AppTest` smoke tests verifying error-free rendering of the shell and all 6 pages.

---

## 📌 Assumptions Stated
1. **Synthetic Telemetry:** Data is generated via seeded physics simulation (`seed=42`) with realistic daily cycles, noise, and 1% dropouts.
2. **5-Minute Replay:** Telemetry intervals are 5 minutes (~432k readings over 60 days) to keep Snowflake storage and warehouse computation low.
3. **Planned Fix Factor:** Scheduled proactive repairs are assumed to take 40% of emergency breakdown time due to pre-staged parts and technician readiness.
4. **Currency Values:** ₹ (INR) downtime costs and parts prices are illustrative industrial manufacturing estimates.
