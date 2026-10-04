from typing import Any, Dict, List, Optional
import duckdb
import pandas as pd
from src.config import BACKEND, DUCKDB_PATH, SNOWFLAKE_CONFIG

class DatabaseBackend:
    """Abstract interface for database backends."""
    def query_df(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        raise NotImplementedError
        
    def execute(self, query: str, params: Optional[List[Any]] = None) -> None:
        raise NotImplementedError

class DuckDBBackend(DatabaseBackend):
    def __init__(self, db_path: str = str(DUCKDB_PATH)):
        self.db_path = db_path
        
    def _get_connection(self, read_only: bool = False):
        return duckdb.connect(self.db_path, read_only=read_only)
        
    def query_df(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        with self._get_connection(read_only=True) as con:
            if params:
                return con.execute(query, params).df()
            return con.execute(query).df()
            
    def execute(self, query: str, params: Optional[List[Any]] = None) -> None:
        with self._get_connection(read_only=False) as con:
            if params:
                con.execute(query, params)
            else:
                con.execute(query)

class SnowflakeBackend(DatabaseBackend):
    """Snowflake backend stub for PRD 2 execution."""
    def __init__(self, config: Dict[str, Any] = SNOWFLAKE_CONFIG):
        self.config = config
        
    def _get_connection(self):
        try:
            import snowflake.connector
            return snowflake.connector.connect(
                user=self.config["user"],
                password=self.config["password"],
                account=self.config["account"],
                warehouse=self.config["warehouse"],
                database=self.config["database"],
                schema=self.config["schema"],
                role=self.config.get("role", "PULSEOPS_ADMIN")
            )
        except ImportError:
            raise RuntimeError("snowflake-connector-python is not installed. Use local DuckDB backend.")

    def query_df(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            return cur.fetch_pandas_all()
        finally:
            conn.close()

    def execute(self, query: str, params: Optional[List[Any]] = None) -> None:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
        finally:
            conn.close()

# Factory
def get_db() -> DatabaseBackend:
    if BACKEND.lower() == "snowflake":
        return SnowflakeBackend()
    return DuckDBBackend()

# High-Level Data Access Methods
def get_fleet_kpis() -> Dict[str, Any]:
    db = get_db()
    from src.metrics import calculate_fleet_oee, calculate_mtbf_mttr, calculate_total_downtime_cost
    oee = calculate_fleet_oee()
    rel = calculate_mtbf_mttr()
    cost = calculate_total_downtime_cost()
    
    # Active open alerts count
    alerts_df = db.query_df("SELECT COUNT(*) AS cnt FROM ALERTS WHERE status = 'OPEN'")
    open_alerts = int(alerts_df.iloc[0]["cnt"]) if len(alerts_df) > 0 else 0
    
    return {
        "oee": oee["oee"],
        "availability": oee["availability"],
        "performance": oee["performance"],
        "quality": oee["quality"],
        "open_alerts": open_alerts,
        "downtime_cost_inr": cost,
        "mtbf_hours": rel["mtbf_hours"],
        "mttr_hours": rel["mttr_hours"],
        "total_failures": rel["total_failures"]
    }

def get_alerts(plant_id: Optional[str] = None, status: Optional[str] = None) -> pd.DataFrame:
    db = get_db()
    query = """
        SELECT 
            al.alert_id,
            al.asset_id,
            a.asset_name,
            a.plant_id,
            a.line_id,
            a.asset_type,
            a.criticality,
            a.downtime_cost_per_hr_inr,
            al.created_ts,
            al.risk_score,
            al.predicted_failure_mode,
            al.predicted_window_hrs,
            al.top_signals,
            al.status,
            -- Risk Rank Score = Risk * Criticality * Downtime Cost
            ROUND(al.risk_score * a.criticality * (a.downtime_cost_per_hr_inr / 1000.0), 2) AS priority_score
        FROM ALERTS al
        JOIN ASSETS a ON al.asset_id = a.asset_id
        WHERE 1=1
    """
    params: List[Any] = []
    if plant_id and plant_id != "All Plants":
        query += " AND a.plant_id = ?"
        params.append(plant_id)
    if status and status != "All Statuses":
        query += " AND al.status = ?"
        params.append(status)
        
    query += " ORDER BY priority_score DESC, al.risk_score DESC"
    return db.query_df(query, params or None)

def get_asset_details(asset_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    df = db.query_df("SELECT * FROM ASSETS WHERE asset_id = ?", [asset_id])
    if len(df) == 0:
        return None
    return df.iloc[0].to_dict()

def get_sensor_telemetry(asset_id: str, hours: int = 72) -> pd.DataFrame:
    db = get_db()
    # Get last N hours of telemetry
    limit_rows = int((hours * 60) / 5)
    query = f"""
        SELECT 
            reading_ts,
            vibration_mm_s,
            temperature_c,
            rpm,
            motor_current_a
        FROM SENSOR_READINGS
        WHERE asset_id = ?
        ORDER BY reading_ts DESC
        LIMIT {limit_rows}
    """
    df = db.query_df(query, [asset_id])
    return df.sort_values(by="reading_ts").reset_index(drop=True)

def get_maintenance_history(asset_id: Optional[str] = None, limit: int = 10) -> pd.DataFrame:
    db = get_db()
    params: List[Any] = []
    if asset_id:
        query = "SELECT * FROM MAINTENANCE_ORDERS WHERE asset_id = ? ORDER BY created_ts DESC LIMIT ?"
        params = [asset_id, limit]
    else:
        query = "SELECT * FROM MAINTENANCE_ORDERS ORDER BY created_ts DESC LIMIT ?"
        params = [limit]
    return db.query_df(query, params)

def get_spare_parts_catalog(asset_type: Optional[str] = None) -> pd.DataFrame:
    db = get_db()
    if asset_type:
        query = "SELECT * FROM SPARE_PARTS WHERE compatible_asset_type = ? ORDER BY lead_time_days ASC, qty_on_hand DESC"
        return db.query_df(query, [asset_type])
    return db.query_df("SELECT * FROM SPARE_PARTS ORDER BY lead_time_days ASC, qty_on_hand DESC")

def search_knowledge_docs(query: str = "", asset_type: Optional[str] = None) -> pd.DataFrame:
    db = get_db()
    sql = "SELECT doc_id, title, asset_type, doc_type, body FROM KNOWLEDGE_DOCS WHERE 1=1"
    params: List[Any] = []
    if asset_type:
        sql += " AND asset_type = ?"
        params.append(asset_type)
    if query:
        # Sanitize words: only allow alphanumeric, spaces, hyphens for LIKE safety
        import re as _re
        words = [_re.sub(r"[^\w\s-]", "", w.strip()) for w in query.lower().split() if len(w.strip()) > 2]
        words = [w for w in words if w]  # drop empty after sanitize
        if words:
            # DuckDB supports ? in LIKE patterns via params
            clauses = ["(LOWER(title) LIKE ? OR LOWER(body) LIKE ?)" for _ in words]
            sql += " AND (" + " OR ".join(clauses) + ")"
            for w in words:
                params.extend([f"%{w}%", f"%{w}%"])
    return db.query_df(sql, params or None)

def update_alert_status(alert_id: str, new_status: str) -> None:
    db = get_db()
    db.execute("UPDATE ALERTS SET status = ? WHERE alert_id = ?", [new_status, alert_id])

def create_work_order(
    asset_id: str,
    failure_mode: str,
    part_name: str,
    technician_notes: str,
    labor_hours: float = 3.0,
    cost_inr: int = 5000,
    order_type: str = "PREVENTIVE"
) -> str:
    db = get_db()
    from datetime import datetime
    
    # Generate unique ID
    existing = db.query_df("SELECT COUNT(*) AS cnt FROM MAINTENANCE_ORDERS")
    cnt = int(existing.iloc[0]["cnt"]) + 1001
    order_id = f"ORD_{cnt}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    sql = """
        INSERT INTO MAINTENANCE_ORDERS (
            order_id, asset_id, order_type, source, status,
            created_ts, completed_ts, failure_mode, parts_used,
            labor_hours, cost_inr, technician_notes
        ) VALUES (
            ?, ?, ?, 'PULSEOPS', 'SCHEDULED',
            ?, NULL, ?, ?, ?, ?, ?
        )
    """
    db.execute(sql, [
        order_id, asset_id, order_type, now_str,
        failure_mode, part_name, labor_hours, cost_inr, technician_notes
    ])
    return order_id
