import random
from datetime import datetime, timedelta
import duckdb
import numpy as np
import pandas as pd
from src.config import DATA_DIR, DUCKDB_PATH

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

def generate_all_data():
    print("Generating PulseOps synthetic data (seed=42)...")
    
    # 1. ASSETS
    # 25 assets across 3 plants and 5 lines
    plants = ["PLANT_PUNE", "PLANT_CHENNAI", "PLANT_GURUGRAM"]
    asset_types = [
        ("CNC", 1800, 45, 12000),
        ("Pump", 1500, 30, 8000),
        ("Compressor", 3000, 60, 15000),
        ("Conveyor Motor", 1200, 20, 6000),
        ("Press", 900, 90, 20000)
    ]
    
    assets_data = []
    asset_id_counter = 101
    
    # Distribute 25 assets across 3 plants (9 in Pune, 8 in Chennai, 8 in Gurugram)
    plant_quotas = {"PLANT_PUNE": 9, "PLANT_CHENNAI": 8, "PLANT_GURUGRAM": 8}
    
    for plant, quota in plant_quotas.items():
        plant_count = 0
        line_idx = 1
        while plant_count < quota and len(assets_data) < 25:
            line_id = f"LINE_{line_idx}"
            for (atype, rated_rpm, ideal_cycle_sec, cost_per_hr) in asset_types:
                if plant_count >= quota or len(assets_data) >= 25:
                    break
                criticality = random.choices([1, 2, 3, 4, 5], weights=[0.1, 0.15, 0.35, 0.25, 0.15])[0]
                install_days_ago = random.randint(300, 1800)
                install_date = (datetime(2026, 1, 1) - timedelta(days=install_days_ago)).strftime("%Y-%m-%d")
                
                assets_data.append({
                    "asset_id": f"AST_{asset_id_counter}",
                    "asset_name": f"{atype} {line_id}-{asset_id_counter % 100:02d}",
                    "plant_id": plant,
                    "line_id": line_id,
                    "asset_type": atype,
                    "criticality": criticality,
                    "install_date": install_date,
                    "rated_rpm": rated_rpm,
                    "ideal_cycle_time_sec": ideal_cycle_sec,
                    "downtime_cost_per_hr_inr": cost_per_hr
                })
                asset_id_counter += 1
                plant_count += 1
            line_idx += 1

    df_assets = pd.DataFrame(assets_data)
    print(f"Generated {len(df_assets)} assets.")

    # 2. SPARE PARTS
    spare_parts_catalog = [
        ("Bearing Set 6205-2RS", "CNC", 12, 3, 4500),
        ("High-Precision Spindle Bearing", "CNC", 4, 7, 24000),
        ("Mechanical Shaft Seal Kit", "Pump", 8, 2, 3200),
        ("Impeller Assembly 316SS", "Pump", 3, 10, 18500),
        ("Synthetic Lubricant ISO VG 68 (20L)", "Compressor", 15, 1, 6500),
        ("Rotary Screw Valve Overhaul Kit", "Compressor", 5, 5, 28000),
        ("Drive Belt Heavy-Duty 5V", "Conveyor Motor", 20, 1, 1800),
        ("Stator Winding Overhaul Kit", "Conveyor Motor", 2, 14, 35000),
        ("Hydraulic Pressure Relief Valve", "Press", 6, 4, 12500),
        ("Main Hydraulic Cylinder Seal Kit", "Press", 3, 8, 42000),
        ("Universal Vibration Isolator Mount", "CNC", 25, 1, 1200),
        ("Motor Cooling Fan Shroud", "Pump", 10, 2, 2800),
    ]
    parts_data = []
    for idx, (pname, atype, qty, lead_days, cost) in enumerate(spare_parts_catalog, start=1):
        parts_data.append({
            "part_id": f"PRT_{idx:03d}",
            "part_name": pname,
            "compatible_asset_type": atype,
            "qty_on_hand": qty,
            "lead_time_days": lead_days,
            "unit_cost_inr": cost
        })
    df_spare_parts = pd.DataFrame(parts_data)
    print(f"Generated {len(df_spare_parts)} spare parts.")

    # 3. KNOWLEDGE DOCS (~40 docs)
    doc_templates = [
        ("SOP-001: Bearing Vibration Diagnostic & Replacement", "CNC", "SOP",
         "When RMS vibration exceeds 4.5 mm/s on CNC spindle bearings (ISO 10816-3 Zone C), conduct spectral analysis. If 1X/2X harmonics are elevated, check preload. Replace with Bearing Set 6205-2RS within 48h to prevent catastrophic tool damage."),
        ("SOP-002: Pump Shaft Realignment and Soft Foot Correction", "Pump", "SOP",
         "Vibration exceeding 5.0 mm/s at 1X rotational speed indicates coupling misalignment. Check radial and axial runout using laser alignment tool. Re-torque base bolts to 85 Nm and inspect Mechanical Shaft Seal Kit."),
        ("SOP-003: Compressor Thermal Overload and Lubrication Servicing", "Compressor", "SOP",
         "When discharge temperature crosses 88°C accompanied by current creep above 42A, inspect oil separator differential pressure. Top up with Synthetic Lubricant ISO VG 68. Flush cooling radiator if delta T exceeds 15°C."),
        ("SOP-004: Conveyor Motor Stator Insulation Degradation Protocol", "Conveyor Motor", "SOP",
         "Phase current imbalances >10% and current spikes indicate stator insulation breakdown. Measure winding resistance with Megger tester (>50 Mohm required). If resistance drops below 5 Mohm, swap stator assembly."),
        ("SOP-005: Hydraulic Press Proportional Valve Calibration", "Press", "SOP",
         "Pressure fluctuations during dwell cycle signify sticking proportional spool. Clean pilot filter, check relief valve response, and recalibrate LVDT sensor feedback loop."),
        ("TECH-011: Root Cause Analysis: Micro-Pitting in CNC High-Speed Spindles", "CNC", "TECH_NOTE",
         "Investigation into recurring AST_101 vibration spikes revealed electrical discharge machining (EDM) effect from VFD common-mode voltage. Grounding brush installation recommended."),
        ("TECH-012: Cavitation Dynamics in Slurry Transfer Pumps", "Pump", "TECH_NOTE",
         "NPSH margin depletion at AST_107 causes localized vapor collapse, pitting impellers and elevating 2.5kHz-5kHz band vibration. Maintain suction head ≥ 2.4 bar."),
        ("TECH-013: Vane Wear Signatures in Rotary Screw Compressors", "Compressor", "TECH_NOTE",
         "Compressor AST_113 exhibited thermal creep from 72°C to 94°C over 36 hours prior to trip. Precursor signature: current ramp 18% above baseline with high-frequency acoustic emission."),
        ("TECH-014: Stator Thermal Fatigue Under Shock Loadings", "Conveyor Motor", "TECH_NOTE",
         "Intermittent jam events on stamping conveyor create 250% inrush currents, degrading Class F insulation within 18 months."),
        ("TECH-015: Hydraulic Cavitation in Fast-Acting Press Cylinders", "Press", "TECH_NOTE",
         "Rapid decompression profiles cause aeration and seal degradation in AST_122. Modify decompression ramp to 120ms.")
    ]

    docs_data = []
    doc_id = 1
    for template in doc_templates:
        docs_data.append({
            "doc_id": f"DOC_{doc_id:03d}",
            "title": template[0],
            "asset_type": template[1],
            "doc_type": template[2],
            "body": template[3]
        })
        doc_id += 1

    # Add failure reports for specific historical failures
    for ast in df_assets.itertuples():
        docs_data.append({
            "doc_id": f"DOC_{doc_id:03d}",
            "title": f"FAILURE_REPORT: Past Breakdown on {ast.asset_name} ({ast.asset_id})",
            "asset_type": ast.asset_type,
            "doc_type": "FAILURE_REPORT",
            "body": f"Historical incident report for {ast.asset_name} at {ast.plant_id}, {ast.line_id}. Asset suffered unexpected stoppage due to unchecked {ast.asset_type.lower()} fault. Downtime recorded: 5.5 hours. Recommended tighter telemetry monitoring on vibration and temperature."
        })
        doc_id += 1
        if len(docs_data) >= 42:
            break

    df_docs = pd.DataFrame(docs_data)
    print(f"Generated {len(df_docs)} knowledge documents.")

    # 4. SENSOR READINGS & FAILURE EVENTS
    # 60 days at 5-minute intervals = 60 * 24 * 12 = 17,280 timestamps per asset
    # 25 assets * 17,280 = 432,000 rows
    start_time = datetime(2026, 8, 1, 0, 0, 0)
    total_intervals = 60 * 24 * 12
    timestamps = [start_time + timedelta(minutes=5 * i) for i in range(total_intervals)]
    
    # Pre-plan 22 failure events across 60 days
    # Time split: Train = first 40 days (intervals 0 to 11520), Test = last 20 days (intervals 11520 to 17280)
    failure_modes = [
        "Bearing wear", 
        "Misalignment", 
        "Overheating / lubrication loss", 
        "Motor winding fault"
    ]
    
    # 14 failures in train period, 8 failures in test period
    failure_events = []
    
    train_fail_times = sorted(random.sample(range(2000, 11000), 14))
    test_fail_times = sorted(random.sample(range(12000, 16800), 8))
    all_fail_times = train_fail_times + test_fail_times
    
    sampled_assets = random.choices(df_assets["asset_id"].tolist(), k=len(all_fail_times))
    
    for f_idx, fail_interval in enumerate(all_fail_times):
        asset_id = sampled_assets[f_idx]
        f_mode = failure_modes[f_idx % len(failure_modes)]
        
        # Ramp durations in intervals (5-min steps)
        if f_mode == "Bearing wear":
            ramp_hours = random.uniform(48, 96)
        elif f_mode == "Misalignment":
            ramp_hours = random.uniform(24, 72)
        elif f_mode == "Overheating / lubrication loss":
            ramp_hours = random.uniform(24, 48)
        else: # Motor winding fault
            ramp_hours = random.uniform(12, 36)
            
        ramp_intervals = int((ramp_hours * 60) / 5)
        start_interval = max(0, fail_interval - ramp_intervals)
        
        failure_events.append({
            "event_id": f"EVT_{f_idx+1:02d}",
            "asset_id": asset_id,
            "failure_mode": f_mode,
            "start_interval": start_interval,
            "fail_interval": fail_interval,
            "fail_ts": timestamps[fail_interval],
            "start_ts": timestamps[start_interval],
            "ramp_hours": ramp_hours,
            "is_test_split": (fail_interval >= 11520)
        })

    # Generate sensor readings dataframe efficiently using numpy
    print("Synthesizing 432,000 telemetry readings with physics simulation...")
    
    all_sensor_rows = []
    
    # Asset baselines lookup
    asset_dict = {a["asset_id"]: a for a in assets_data}
    
    # Pre-calculate time series per asset
    for ast_id, a_meta in asset_dict.items():
        base_rpm = float(a_meta["rated_rpm"])
        base_vib = 1.8 + (a_meta["criticality"] * 0.2)
        base_temp = 52.0 + (a_meta["criticality"] * 1.5)
        base_curr = 22.0 + (a_meta["criticality"] * 3.0)
        
        # Base daily cycles (24h = 288 steps)
        step_arr = np.arange(total_intervals)
        daily_cycle = np.sin(2 * np.pi * step_arr / 288) * 0.15
        
        # Normal baseline noise
        vib = base_vib + daily_cycle + np.random.normal(0, 0.15, total_intervals)
        temp = base_temp + daily_cycle * 2.0 + np.random.normal(0, 0.4, total_intervals)
        rpm = base_rpm + np.random.normal(0, 8.0, total_intervals)
        curr = base_curr + daily_cycle * 1.5 + np.random.normal(0, 0.3, total_intervals)
        
        # False alarm bump (does not end in failure) around day 15 or 45
        false_bump_start = random.choice([4000, 13000])
        bump_len = 120 # 10 hours
        vib[false_bump_start:false_bump_start+bump_len] += np.sin(np.pi * np.arange(bump_len) / bump_len) * 1.6
        temp[false_bump_start:false_bump_start+bump_len] += np.sin(np.pi * np.arange(bump_len) / bump_len) * 3.0
        
        # Inject real failure physics ramps
        ast_fails = [f for f in failure_events if f["asset_id"] == ast_id]
        for f in ast_fails:
            s_idx = f["start_interval"]
            e_idx = f["fail_interval"]
            L = e_idx - s_idx
            if L > 0:
                progress = np.linspace(0, 1, L)
                f_mode = f["failure_mode"]
                if f_mode == "Bearing wear":
                    # Vibration climbs steadily (e.g. +4.5 mm/s), temp rises modestly
                    vib[s_idx:e_idx] += (progress ** 1.8) * 5.2
                    temp[s_idx:e_idx] += (progress ** 1.2) * 8.0
                    curr[s_idx:e_idx] += (progress ** 1.5) * 2.5
                elif f_mode == "Misalignment":
                    # High vibration at steady RPM; current slightly up
                    vib[s_idx:e_idx] += (progress ** 1.3) * 6.5
                    curr[s_idx:e_idx] += (progress ** 1.1) * 3.5
                    temp[s_idx:e_idx] += progress * 4.0
                elif f_mode == "Overheating / lubrication loss":
                    # Temperature climbs sharply; current rises
                    temp[s_idx:e_idx] += (progress ** 1.5) * 26.0
                    curr[s_idx:e_idx] += (progress ** 1.4) * 8.0
                    vib[s_idx:e_idx] += (progress ** 2.0) * 3.0
                elif f_mode == "Motor winding fault":
                    # Current spikes/instability; RPM drops under load
                    curr[s_idx:e_idx] += (progress ** 1.2) * 18.0 + np.random.normal(0, 2.5, L)
                    rpm[s_idx:e_idx] -= (progress ** 1.5) * (base_rpm * 0.12)
                    temp[s_idx:e_idx] += progress * 12.0
                    vib[s_idx:e_idx] += progress * 2.5
                    
                # Post-failure drop (asset stops for 4-8 hours)
                downtime_len = random.randint(48, 96) # 4 to 8 hours
                post_end = min(total_intervals, e_idx + downtime_len)
                rpm[e_idx:post_end] = 0.0
                curr[e_idx:post_end] = 0.0
                temp[e_idx:post_end] = 30.0
                vib[e_idx:post_end] = 0.05
        
        # 1% sensor dropouts / missing noise
        dropout_mask = np.random.rand(total_intervals) < 0.01
        vib[dropout_mask] = np.nan
        temp[dropout_mask] = np.nan
        rpm[dropout_mask] = np.nan
        curr[dropout_mask] = np.nan
        
        # Interpolate NaNs cleanly to keep realistic
        s_vib = pd.Series(vib).interpolate().bfill().values
        s_temp = pd.Series(temp).interpolate().bfill().values
        s_rpm = pd.Series(rpm).interpolate().bfill().values
        s_curr = pd.Series(curr).interpolate().bfill().values
        
        ast_df = pd.DataFrame({
            "reading_ts": timestamps,
            "asset_id": ast_id,
            "vibration_mm_s": np.round(np.clip(s_vib, 0.01, 25.0), 3),
            "temperature_c": np.round(np.clip(s_temp, 15.0, 130.0), 2),
            "rpm": np.round(np.clip(s_rpm, 0.0, base_rpm * 1.2), 1),
            "motor_current_a": np.round(np.clip(s_curr, 0.0, 80.0), 2)
        })
        all_sensor_rows.append(ast_df)
        
    df_sensors = pd.concat(all_sensor_rows, ignore_index=True)
    print(f"Generated {len(df_sensors):,} sensor readings.")

    # 5. MAINTENANCE ORDERS
    # Create emergency/corrective orders for each failure event + routine preventive orders
    orders_data = []
    order_counter = 1001
    
    for f in failure_events:
        ast_meta = asset_dict[f["asset_id"]]
        created = f["fail_ts"]
        downtime_hours = random.uniform(3.5, 7.5)
        completed = created + timedelta(hours=downtime_hours)
        labor_hours = round(downtime_hours * 2.0, 1)
        
        # Find parts used
        compat_parts = df_spare_parts[df_spare_parts["compatible_asset_type"] == ast_meta["asset_type"]]
        part_name = compat_parts.iloc[0]["part_name"] if len(compat_parts) > 0 else "Bearing Set"
        part_cost = float(compat_parts.iloc[0]["unit_cost_inr"]) if len(compat_parts) > 0 else 5000
        cost_inr = int(part_cost + (labor_hours * 1200))
        
        orders_data.append({
            "order_id": f"ORD_{order_counter}",
            "asset_id": f["asset_id"],
            "order_type": "EMERGENCY",
            "source": "HISTORICAL",
            "status": "COMPLETED",
            "created_ts": created.strftime("%Y-%m-%d %H:%M:%S"),
            "completed_ts": completed.strftime("%Y-%m-%d %H:%M:%S"),
            "failure_mode": f["failure_mode"],
            "parts_used": part_name,
            "labor_hours": labor_hours,
            "cost_inr": cost_inr,
            "technician_notes": f"Emergency corrective repair for {f['failure_mode']}. Replaced {part_name}. Tested rotation at rated RPM."
        })
        order_counter += 1
        
    # Add routine preventive maintenance orders
    for ast_id in asset_dict.keys():
        for pm_day in [10, 25, 40, 55]:
            pm_created = start_time + timedelta(days=pm_day, hours=random.randint(6, 18))
            pm_completed = pm_created + timedelta(hours=random.uniform(1.0, 2.5))
            orders_data.append({
                "order_id": f"ORD_{order_counter}",
                "asset_id": ast_id,
                "order_type": "PREVENTIVE",
                "source": "HISTORICAL",
                "status": "COMPLETED",
                "created_ts": pm_created.strftime("%Y-%m-%d %H:%M:%S"),
                "completed_ts": pm_completed.strftime("%Y-%m-%d %H:%M:%S"),
                "failure_mode": "None (Routine)",
                "parts_used": "Lubrication / Filter",
                "labor_hours": 2.0,
                "cost_inr": 2500,
                "technician_notes": "Quarterly inspection and greasing. Asset operating within nominal tolerance."
            })
            order_counter += 1

    df_orders = pd.DataFrame(orders_data)
    print(f"Generated {len(df_orders)} maintenance orders.")

    # 6. PRODUCTION RUNS (60 days, 3 shifts/day = 180 shifts per asset)
    # 25 assets * 180 shifts = 4,500 rows
    prod_runs = []
    run_counter = 5001
    
    shifts = [
        ("A", 6, 14),   # Morning 06:00 - 14:00 (480 mins)
        ("B", 14, 22),  # Evening 14:00 - 22:00 (480 mins)
        ("C", 22, 6)    # Night 22:00 - 06:00 (480 mins)
    ]
    
    for day in range(60):
        current_date = (start_time + timedelta(days=day)).date()
        for shift_name, start_hr, end_hr in shifts:
            shift_start_ts = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=start_hr)
            shift_end_ts = shift_start_ts + timedelta(hours=8)
            
            for ast_id, a_meta in asset_dict.items():
                planned_mins = 480
                ideal_cycle = a_meta["ideal_cycle_time_sec"]
                ideal_units = int((planned_mins * 60) / ideal_cycle)
                
                # Check if asset had a breakdown during this shift
                overlapping_fails = [
                    f for f in failure_events 
                    if f["asset_id"] == ast_id and shift_start_ts <= f["fail_ts"] <= shift_end_ts
                ]
                
                if overlapping_fails:
                    downtime_mins = random.randint(180, 360)
                    run_mins = planned_mins - downtime_mins
                    speed_factor = random.uniform(0.80, 0.92)
                    quality_factor = random.uniform(0.85, 0.94)
                else:
                    downtime_mins = random.choices([0, 15, 30, 45], weights=[0.8, 0.1, 0.06, 0.04])[0]
                    run_mins = planned_mins - downtime_mins
                    speed_factor = random.uniform(0.92, 0.99)
                    quality_factor = random.uniform(0.96, 0.995)
                    
                actual_units = int((run_mins * 60 / ideal_cycle) * speed_factor)
                good_units = int(actual_units * quality_factor)
                
                prod_runs.append({
                    "run_id": f"RUN_{run_counter}",
                    "asset_id": ast_id,
                    "shift_date": str(current_date),
                    "shift": shift_name,
                    "planned_minutes": planned_mins,
                    "run_minutes": run_mins,
                    "downtime_minutes": downtime_mins,
                    "ideal_units": ideal_units,
                    "actual_units": actual_units,
                    "good_units": good_units
                })
                run_counter += 1

    df_prod_runs = pd.DataFrame(prod_runs)
    print(f"Generated {len(df_prod_runs)} production runs.")

    # 7. INITIAL ALERTS TABLE (Empty or seeded with active alerts)
    df_alerts = pd.DataFrame(columns=[
        "alert_id", "asset_id", "created_ts", "risk_score", 
        "predicted_failure_mode", "predicted_window_hrs", "top_signals", "status"
    ])

    # Save to CSV and Parquet in data/
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    tables = {
        "ASSETS": df_assets,
        "SPARE_PARTS": df_spare_parts,
        "KNOWLEDGE_DOCS": df_docs,
        "SENSOR_READINGS": df_sensors,
        "MAINTENANCE_ORDERS": df_orders,
        "PRODUCTION_RUNS": df_prod_runs,
        "ALERTS": df_alerts
    }
    
    for tname, df in tables.items():
        csv_path = DATA_DIR / f"{tname.lower()}.csv"
        parquet_path = DATA_DIR / f"{tname.lower()}.parquet"
        df.to_csv(csv_path, index=False)
        df.to_parquet(parquet_path, index=False)
        print(f"Saved {tname} -> {csv_path.name} & {parquet_path.name}")
        
    # Load directly into DuckDB
    print(f"Loading tables into DuckDB at {DUCKDB_PATH}...")
    con = duckdb.connect(str(DUCKDB_PATH))
    for tname, df in tables.items():
        con.execute(f"CREATE OR REPLACE TABLE {tname} AS SELECT * FROM df")
    con.close()
    print("DuckDB database populated successfully.")
    
    return failure_events

if __name__ == "__main__":
    generate_all_data()
