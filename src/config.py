import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

BACKEND = os.getenv("BACKEND", "local")
DUCKDB_PATH = BASE_DIR / os.getenv("DUCKDB_PATH", "data/pulseops.duckdb")

RISK_THRESHOLD = float(os.getenv("RISK_THRESHOLD", "0.65"))
ALERT_WINDOW_HOURS = int(os.getenv("ALERT_WINDOW_HOURS", "72"))

# Snowflake settings
SNOWFLAKE_CONFIG = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT", ""),
    "user": os.getenv("SNOWFLAKE_USER", ""),
    "password": os.getenv("SNOWFLAKE_PASSWORD", ""),
    "database": os.getenv("SNOWFLAKE_DATABASE", "PULSEOPS_PROD"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA", "CORE"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "PULSEOPS_XS_WH"),
    "role": os.getenv("SNOWFLAKE_ROLE", "PULSEOPS_ADMIN"),
}
