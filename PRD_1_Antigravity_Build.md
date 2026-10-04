# PRD 1 of 2 — PulseOps: Build Everything (Antigravity)

**Product:** PulseOps — Predictive Maintenance & OEE Command Center
**Hackathon:** Snowflake CoCo CLI Hackathon (GCC Edition), problem statement "Predictive Maintenance and OEE Command Center"
**This PRD's job:** Build the *complete* product locally, start to finish, so that a second tool (Snowflake CoCo, PRD 2) only has to connect the database, deploy and test.
**Judging weights to design for:** Technical Execution 40% · Real-World Relevance 30% · Solution Completeness 30%

---

## 1. Ground rules for the builder (read first)

1. **Local-first.** Everything must run end to end on local data with one command. No Snowflake account is needed to finish this PRD.
2. **Snowflake-ready, not Snowflake-run.** Write all Snowflake artifacts (SQL, YAML, agent spec, deployment notes) as files in `/snowflake`. Do **not** execute anything against Snowflake in this phase.
3. **Backend switch.** One data-access interface with two backends, selected by `BACKEND=local|snowflake` in `.env`. Local = DuckDB. The Snowflake backend is written now (Snowpark / connector) but untested.
4. **One source of truth for metrics.** OEE, MTBF, MTTR defined once in code and once in the semantic view; they must match (golden values below).
5. **Honesty over polish.** Synthetic data only, honest model metrics, assumptions stated on screen and in the README.
6. **Quality bar.** Clean structure, typed Python where reasonable, config in `.env`/`config.yaml`, no secrets in git, no raw tracebacks in the UI, clear empty/loading/error states.

## 2. Problem and vision

Manufacturers lose value to unplanned downtime because OT sensor data (vibration, temperature, RPM) sits apart from ERP/maintenance context (work orders, spare parts, production). Teams react to breakdowns and cannot quickly answer "why did OEE drop on Line 3?"

PulseOps converges both worlds. A maintenance planner can (1) see fleet health and a ranked alert queue, (2) understand why an asset is at risk, (3) ask questions in natural language with cited evidence, (4) approve an AI-drafted work order in one click, and (5) see the OEE and ₹ impact of acting early.

**Users:** Maintenance planner (primary) · Plant manager · Reliability engineer.

## 3. Scope

**P0 (must ship)**
1. Synthetic data generator (consistent, realistic failures)
2. Unified data model + metric definitions
3. Failure prediction (risk score, predicted window, likely failure mode)
4. Command center UI: fleet view, alert queue, asset drill-down
5. Natural-language root-cause chat (data + documents, with citations)
6. Work-order flow: draft → human approval → record created
7. OEE impact panel (baseline vs with-PulseOps)
8. Snowflake deployment pack + handoff files for PRD 2

**P1 (if time allows):** spare-part check inside the work-order draft; Slack/Jira alert stub (interface only); scheduled-scoring script that mirrors the planned Snowflake Task.

**Non-goals:** real plant data, real hardware streaming, production auth, multi-agent orchestration.

## 4. Data specification (synthetic)

Seeded generator (`seed=42`) for reproducibility. **~25 assets across 3 plants, 60 days, 5-minute sensor interval (~430k rows).** Keep it small so Snowflake costs stay low later.

**ASSETS** — `asset_id, asset_name, plant_id, line_id, asset_type (CNC | Pump | Compressor | Conveyor Motor | Press), criticality (1–5), install_date, rated_rpm, ideal_cycle_time_sec, downtime_cost_per_hr_inr`

**SENSOR_READINGS** — `reading_ts, asset_id, vibration_mm_s, temperature_c, rpm, motor_current_a`

**MAINTENANCE_ORDERS** — `order_id, asset_id, order_type (PREVENTIVE | CORRECTIVE | EMERGENCY), source (HISTORICAL | PULSEOPS), status, created_ts, completed_ts, failure_mode, parts_used, labor_hours, cost_inr, technician_notes`

**PRODUCTION_RUNS** — `run_id, asset_id, shift_date, shift (A|B|C), planned_minutes, run_minutes, downtime_minutes, ideal_units, actual_units, good_units`

**SPARE_PARTS** — `part_id, part_name, compatible_asset_type, qty_on_hand, lead_time_days, unit_cost_inr`

**KNOWLEDGE_DOCS** — `doc_id, title, asset_type, doc_type (SOP | TECH_NOTE | FAILURE_REPORT), body` (~40 short docs: SOP per failure mode, past failure reports, technician notes)

**ALERTS** — `alert_id, asset_id, created_ts, risk_score, predicted_failure_mode, predicted_window_hrs, top_signals, status (OPEN | ACK | ACTIONED | DISMISSED)`

### Failure physics (≈18–25 failure events in 60 days)

| Failure mode | Signature before failure | Ramp |
|---|---|---|
| Bearing wear | Vibration climbs steadily; temperature rises modestly | 48–96 h |
| Misalignment | High vibration at steady RPM; current slightly up | 24–72 h |
| Overheating / lubrication loss | Temperature climbs; current rises | 24–48 h |
| Motor winding fault | Current spikes/instability; RPM drops under load | 12–36 h |

Realism requirements: daily load cycles, sensor noise, ~1% dropouts, a few false-alarm bumps that do **not** end in failure, a few failures with weak warning. Each failure must also produce downtime in PRODUCTION_RUNS, an EMERGENCY/CORRECTIVE order with notes, and a matching failure report in KNOWLEDGE_DOCS.

## 5. Metric definitions

- Availability = run_minutes / planned_minutes
- Performance = actual_units / ideal_units
- Quality = good_units / actual_units
- **OEE = Availability × Performance × Quality**
- MTBF = operating hours / number of failures
- MTTR = mean(completed_ts − created_ts) for corrective/emergency orders
- Downtime cost = downtime hours × downtime_cost_per_hr_inr

## 6. Functional requirements

**F1 Feature engineering.** Per asset, rolling 1h/6h/24h mean/max/std of vibration, temperature, current; vibration slope; deviation from the asset's own 14-day baseline; RPM variance. Write it as plain SQL-expressible logic so it maps cleanly to Snowflake Dynamic Tables.

**F2 Failure prediction.** Label = failure within next 72h. Gradient-boosted classifier (scikit-learn). **Time-based split** (train first ~40 days, test last ~20); never random split. Output per asset: risk_score, predicted failure mode, estimated window (hours), top contributing signals. Report precision, recall, median lead time, false alarms/week vs a naive baseline in `/reports/model_eval.md`. Alert when risk ≥ configurable threshold → ALERTS row.

**F3 Command center (Streamlit).**
- *Fleet view:* KPI strip (fleet OEE, open alerts, downtime cost this week, failures avoided) + health heatmap by plant/line/asset.
- *Alert queue:* ranked by risk × criticality × downtime cost; filter by plant/status; ack / dismiss / create work order.
- *Asset drill-down:* sensor trends with predicted window shaded, last 5 maintenance orders, spare-part status, plain-language "why flagged", related documents.
- *Chat panel:* F4.
- *OEE impact panel:* F6.

**F4 Natural-language root-cause agent.** Two tool families: (a) structured analytics over the metric layer/SQL ("OEE by line last week"), (b) document search over KNOWLEDGE_DOCS with **cited document titles**. Rules: show the SQL/evidence used; say "I don't have enough data" instead of guessing; never invent a document; decline out-of-scope questions; warn if sensor data is stale. Locally: router + DuckDB SQL + simple retrieval. Tool functions (`run_metric_query`, `search_docs`, `draft_work_order`, `check_spare_parts`, `create_work_order`) must be clean, documented functions so they can later be re-registered as Snowflake tools.

**F5 Work-order automation.** Agent drafts: asset, suspected failure mode, recommended action, parts needed (checked against SPARE_PARTS), proposed window (lowest-production shift), estimated cost avoided. **Human approval required** before inserting into MAINTENANCE_ORDERS (`source='PULSEOPS'`). Write an audit record (approver, time, model score).

**F6 OEE impact simulation.** Replay the 60 days: for each true failure that PulseOps alerted with enough lead time, convert emergency downtime into a shorter planned window (default: planned fix = 40% of emergency downtime, configurable and shown on screen). Show downtime avoided (h), OEE uplift (pp), ₹ saved.

## 7. Trust and guardrails
Confidence shown with every prediction; low-confidence alerts labelled; stale-data warning; no auto-created work orders; out-of-scope refusal; synthetic data only.

## 8. Build order (checkpoint after every step)

1. Scaffold repo, `Makefile` (`setup`, `data`, `train`, `run`, `test`), `.env.example`, README skeleton.
2. Data generator + `validate_data.py` (referential integrity, no negatives, every failure has a visible ramp).
3. DuckDB load + `metrics.py` + unit tests.
4. Features + model + `model_eval.md` + scoring script writing ALERTS.
5. Data-access layer with both backends.
6. Agent tools + router + guardrails + citation formatting.
7. Streamlit app (fleet → queue → drill-down → chat → impact → approval flow).
8. **Snowflake pack** (section 9).
9. Tests + `tests/agent_questions.yaml` (15–20 questions with expected key facts, incl. one out-of-scope and one stale-data case).
10. Architecture diagram (Mermaid), `DEMO.md` (4–5 min script on one failing asset), final README.

## 9. Snowflake deployment pack (`/snowflake`) — written, not run

Numbered, idempotent, parameterised files (database/schema/warehouse names in one `config.sql` or variables block):

- `00_setup.sql` — database, schema, **XS warehouse with 60s auto-suspend**, resource monitor with a hard credit cap
- `01_stage_and_load.sql` — stage, file format, COPY from the generated files for all tables
- `02_features.sql` — feature layer as Dynamic Tables (mirrors F1)
- `03_scoring.sql` — notes/SQL for scoring; plus a documented fallback to load locally-scored ALERTS
- `04_semantic_view.yaml` — metrics (OEE, Availability, Performance, Quality, MTBF, MTTR, downtime cost), dimensions (plant, line, asset, type, shift, date), relationships, synonyms, verified queries
- `05_search_service.sql` — search service over KNOWLEDGE_DOCS
- `06_agent_spec` — agent definition: tools (analytics over semantic view, document search, custom work-order tools), instructions mirroring F4 rules
- `07_task.sql` — scheduled task that refreshes features/scoring/alerts
- `08_streamlit_notes.md` — how to run the app against Snowflake (backend switch) and, if feasible, deploy it inside Snowflake
- `DEPLOY.md` — exact run order, expected objects, expected outcomes

The next tool will verify and correct Snowflake syntax against current docs, so mark any syntax you are unsure of with `-- VERIFY`.

## 10. Handoff deliverables for PRD 2 (required)

1. `/handoff/COCO_HANDOFF.md` — project summary, repo map, how to run locally, list of Snowflake objects to create, known gaps, every `-- VERIFY` item.
2. `/handoff/golden_values.json` — values Snowflake must reproduce: row counts per table; fleet OEE per week; OEE by plant; MTBF/MTTR overall; number of failures; top-5 assets by risk at the last timestamp; model metrics.
3. `/tests/agent_questions.yaml` — the Q&A suite.
4. Generated data files in `/data` (CSV or Parquet) ready for staging.

## 11. Acceptance criteria

- [ ] `make setup && make data && make train && make run` works on a fresh clone
- [ ] Alerts for injected failures appear before the failure, with ≥24h median lead time on the test period
- [ ] Model report shows precision, recall, lead time, false alarms/week vs naive baseline
- [ ] Alert → drill-down → "why?" → approve work order takes under 2 minutes
- [ ] Chat cites document titles, shows queries, refuses out-of-scope questions
- [ ] OEE panel shows baseline vs PulseOps with visible assumptions
- [ ] Unit tests pass; agent question suite passes on the local backend
- [ ] Snowflake pack and all handoff files exist and are internally consistent

## 12. Assumptions to state in the README
Synthetic data only; 5-minute replay rather than live streaming; planned-fix duration factor is an assumption; ₹ values are illustrative.
