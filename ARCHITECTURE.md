# PulseOps System Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Data_Generation["1. Physics-Driven Synthetic Data Generator"]
        DG[Data Generator (seed=42)] --> ASSETS[ASSETS (25 Assets across 3 Plants)]
        DG --> SP[SPARE_PARTS]
        DG --> KD[KNOWLEDGE_DOCS (SOPs & Tech Notes)]
        DG --> SENSORS["SENSOR_READINGS (432k Rows, 60 Days @ 5-min)"]
        DG --> PROD[PRODUCTION_RUNS (4.5k Shifts)]
        DG --> MO[MAINTENANCE_ORDERS (Historical Emergencies)]
    end

    subgraph Storage_Layer["2. Unified Data Access Layer (db.py)"]
        ASSETS & SP & KD & SENSORS & PROD & MO --> DUCK[(DuckDB / Local Storage)]
        DUCK -.-> SNOW[(Snowflake / Snowpark)]
    end

    subgraph Analytics_and_ML["3. Feature & Intelligence Engine"]
        SENSORS --> FE[Rolling Features: 1h/6h/24h Mean, Max, Std, Slope, Baseline Dev]
        FE --> ML[HistGradientBoostingClassifier]
        ML --> ALERTS[Ranked Predictive ALERTS Table]
        PROD & ASSETS --> METRICS[Metrics Engine: OEE, Avail, Perf, Qual, MTBF, MTTR]
    end

    subgraph Application_Layer["4. Streamlit Command Center (app/main.py)"]
        METRICS --> V1[Fleet Overview & 25-Asset Heatmap Matrix]
        ALERTS --> V2[Ranked Alert Queue & Work-Order Approval Flow]
        SENSORS & KD --> V3[Asset Telemetry & Diagnostic Drill-Down]
        V2 & V3 --> V4[Root-Cause AI Agent with Cited SOPs & SQL Evidence]
        PROD & ALERTS --> V5[OEE & Financial ROI Impact Simulation]
    end

    subgraph Snowflake_Pack["5. Snowflake Deployment Pack (/snowflake)"]
        SNOW --> S1[00_setup.sql: XS WH + Monitor]
        SNOW --> S2[01_stage_and_load.sql: COPY INTO]
        SNOW --> S3[02_features.sql: Dynamic Tables]
        SNOW --> S4[04_semantic_view.yaml: Cortex Semantic Model]
        SNOW --> S5[05_search_service.sql: Cortex Search]
        SNOW --> S6[06_agent_spec.md: Cortex Analyst]
    end
```
