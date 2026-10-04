# Snowflake CoCo Handoff Guide (PRD 2)

## 1. Project Summary
**Product:** PulseOps — Predictive Maintenance & OEE Command Center  
**Repository State:** Complete local implementation built with DuckDB, Streamlit, Scikit-Learn, and Python.  
**PRD 2 Objective:** Connect to Snowflake, deploy the objects from `/snowflake`, stage the data from `/data`, and verify that the golden values are replicated exactly.

---

## 2. Repository Map
```
.
├── app/
│   ├── main.py                  # Full Streamlit Command Center (5 views)
│   └── styles.css               # Glassmorphism dark UI styling
├── data/
│   ├── *.csv / *.parquet        # Staged synthetic data (432k rows)
│   └── pulseops.duckdb          # Local DuckDB database
├── handoff/
│   ├── COCO_HANDOFF.md          # This handoff documentation
│   └── golden_values.json       # Exact golden benchmarks to verify against
├── reports/
│   └── model_eval.md            # ML evaluation scorecard
├── snowflake/
│   ├── 00_setup.sql             # DB, Schema, XS Warehouse (60s auto-suspend), Monitor
│   ├── 01_stage_and_load.sql    # DDL, file formats, stages, COPY INTO
│   ├── 02_features.sql          # Dynamic Tables for 1h/6h/24h rolling features
│   ├── 03_scoring.sql           # Snowpark scoring & alert generation
│   ├── 04_semantic_view.yaml    # Semantic model for Cortex Analyst
│   ├── 05_search_service.sql    # Cortex Search Service over KNOWLEDGE_DOCS
│   ├── 06_agent_spec.md         # Cortex Intelligence Agent instructions
│   ├── 07_task.sql              # Automated 30-min scoring task
│   ├── 08_streamlit_notes.md    # Streamlit in Snowflake (SiS) guide
│   └── DEPLOY.md                # Execution runbook
├── src/
│   ├── agent.py                 # Root-cause NL agent & tools
│   ├── config.py                # Configuration and env parameters
│   ├── data_generator.py        # Synthetic data generator (seed=42)
│   ├── db.py                    # Data access layer (DuckDB + Snowflake switch)
│   ├── features.py              # Statistical feature engineering
│   ├── metrics.py               # Single source of truth for OEE, MTBF, MTTR
│   ├── model.py                 # Gradient-boosted prediction model
│   ├── simulation.py            # 60-day OEE ROI impact simulation
│   └── validate_data.py         # Integrity & constraint validator
├── tests/
│   ├── agent_questions.yaml     # 16-question automated test suite
│   ├── test_agent.py            # Agent Q&A evaluation runner
│   └── test_metrics.py          # Metric unit tests
└── Makefile                     # Lifecycle automation
```

---

## 3. How to Run Locally
```bash
make setup  # Install dependencies
make data   # Generate & validate data
make train  # Train ML model & score alerts
make test   # Run pytest suite
make run    # Launch Streamlit Command Center
```

---

## 4. Benchmark Golden Values to Verify
Refer to [`golden_values.json`](file:///e:/ishi/hack/New%20folder/handoff/golden_values.json):
- **Fleet OEE:** ~90.8% (Availability: ~98.7%, Performance: ~94.2%, Quality: ~97.7%)
- **Total Sensors Telemetry:** 432,000 rows across 25 assets (60 days at 5-min cadence)
- **Failure Count:** 22 emergency breakdowns (14 train, 8 test)
- **Model Median Lead Time:** 63.8 hours (exceeds ≥ 24h requirement)

---

## 5. Items Marked `-- VERIFY` for Snowflake Deployment
1. `05_search_service.sql`: `SNOWFLAKE.CORTEX.SEARCH_PREVIEW` syntax compatibility in your account's region.
2. `07_task.sql`: `ALTER TASK ... RESUME` requires `EXECUTE TASK` privilege.
