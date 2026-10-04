# Streamlit in Snowflake (SiS) Deployment Guide

## Overview
PulseOps Command Center is built to run natively in Streamlit and can be hosted directly inside Snowflake via **Streamlit in Snowflake (SiS)** or as a local/containerized client connecting via Snowpark.

## Backend Switching
Set the environment variable in your deployment:
```bash
BACKEND=snowflake # switches from local DuckDB to Snowflake connector
```

## Running as a Native SiS App
1. Navigate to Snowflake Snowsight -> **Projects** -> **Streamlit**.
2. Click **+ Streamlit App**.
3. Set Database to `PULSEOPS_PROD`, Schema to `CORE`, Warehouse to `PULSEOPS_XS_WH`.
4. Upload `app/main.py` and `app/styles.css`.
5. Under packages, ensure `pandas`, `numpy`, `plotly`, and `snowflake-snowpark-python` are selected.
6. The app automatically interacts with Snowpark session in place of local DuckDB.
