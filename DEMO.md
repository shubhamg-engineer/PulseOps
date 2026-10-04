# PulseOps Live Demo Walkthrough Script (4–5 Minutes)

**Scenario:** A maintenance planner logs into PulseOps at Plant Pune to triage plant risk, investigate a high-priority predictive failure on CNC machine `AST_101`, consult the AI agent for root-cause evidence, approve a proactive work order, and measure the resulting OEE uplift.

---

### Minute 1: Fleet Health & Heatmap Triage (Tab 1)
1. **Show Fleet KPI Strip:**
   - Fleet OEE: **~90.8%** (Availability: 98.7%, Performance: 94.2%, Quality: 97.7%).
   - Total accumulated downtime cost across 60 days: **~₹1.8 Cr**.
   - Note the **Active High-Risk Alerts** badge highlighted in red.
2. **Scan 25-Asset Heatmap Matrix:**
   - Spot `AST_101` (CNC LINE_1-01 at `PLANT_PUNE`) flagged as **CRITICAL**.
   - Note its criticality level (Level 4/5) and high downtime cost rate (₹12,000/hr).

---

### Minute 2: Ranked Alert Queue & Diagnostic Evidence (Tab 2)
1. **Navigate to Alert Queue:**
   - Observe `AST_101` ranked at the very top with **Priority Score: 30.6** and **Risk Score: ~0.80+**.
   - Review predicted issue: **Bearing wear** with an estimated failure window of **~48 hours**.
   - Review telemetry evidence: `Vibration +3.2 mm/s over baseline, slope 0.65`.
2. **Acknowledge:**
   - Click **Acknowledge Alert** to claim ownership.

---

### Minute 3: Asset Deep-Dive & Physics Multi-Sensor Signature (Tab 3)
1. **Inspect 72-Hour Telemetry Graph:**
   - Select `AST_101` in the dropdown.
   - Point out the physical vibration divergence (RMS climbing from 1.8 mm/s towards 5.5 mm/s) while motor current remains relatively stable, matching the classic ISO 10816-3 bearing degradation curve.
2. **Review Compatible Parts & SOPs:**
   - Compatible parts table shows `Bearing Set 6205-2RS` with **12 units in stock** (Lead time: 3 days).
   - Technical documentation displays `SOP-001: Bearing Vibration Diagnostic & Replacement`.

---

### Minute 4: Root-Cause Agent & Work Order Approval (Tabs 4 & 2)
1. **Ask Root-Cause AI Agent:**
   - Prompt: *"Why is AST_101 at risk and what procedure should I follow?"*
   - Agent outputs structured diagnosis, citing `SOP-001` and current vibration trends with exact SQL transparency.
2. **Draft & Approve Work Order:**
   - In Tab 2, click **Draft Proactive Work Order**.
   - Review AI draft: Proposes off-peak execution during **Shift C (Night 22:00 - 06:00)**, allocates `Bearing Set 6205-2RS`, and calculates **₹48,000 downtime cost avoided**.
   - Click **Approve & Dispatch Work Order** -> Generates `ORD_1023` in `MAINTENANCE_ORDERS` with `source='PULSEOPS'`.

---

### Minute 5: OEE & Financial ROI Simulation (Tab 5)
1. **Open Impact Simulation Panel:**
   - Set the planned fix slider to 40% (pre-staged parts & scheduled window).
   - Review the 60-day operational replay:
     - **Downtime Hours Avoided:** **~48.5 Hours** (33% reduction in emergency downtime).
     - **OEE Uplift:** **+0.92 percentage points** across the entire manufacturing fleet.
     - **Direct Financial Savings:** **~₹5.8 Lakhs** saved in avoided breakdown losses.
