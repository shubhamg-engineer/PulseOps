# PRD 3 — PulseOps Frontend (Command Center UI) and the Backend↔Frontend Contract

**Companion to:** PRD 1 (Antigravity build) and PRD 2 (CoCo on Snowflake).
**Read order for the builder LLM:** PRD 1 → this PRD → PRD 2. Where this PRD and PRD 1 disagree, **this PRD wins for anything the UI touches** (see section 3, "Required changes to PRD 1").
**Framework:** Streamlit (multipage). No React/Next.js, no separate API server.

---

## 0. Why this document exists (read this first, builder)

An LLM building a full product in one go tends to produce a backend and a UI that *almost* fit: a column called `RISK_SCORE` on one side and `risk_score` on the other, a timestamp with a timezone in one place and without in another, a function that returns a DataFrame where the UI expected a dict, an exception where the UI expected an empty state. Each mismatch costs debugging time you do not have today.

This PRD prevents that by being **contract-first**:

1. The UI never talks to DuckDB or Snowflake. It only calls functions in `services/api.py`.
2. Every function has a fixed name, fixed inputs, fixed output shape, fixed column names and types (section 4).
3. Every function returns a `ServiceResult` envelope and **never raises** into the UI, so a backend failure becomes a friendly message, not a crash.
4. The same contract tests run against both backends (local DuckDB and Snowflake). If they pass on local, the UI will work on Snowflake in Phase 2 without UI changes.

**Rule for the builder:** build `contracts.py` and `services/api.py` (with fake data if needed) *before* any page. Then build pages against the contract. Do not invent fields that are not in section 4; if you need one, add it to the contract first.

---

## 1. Goals and non-goals

**Goals**
- A command center a maintenance planner can use: see fleet health → triage alerts → understand why → ask questions → approve a work order → see impact.
- Zero backend-specific code in pages.
- A demo that *tells a story*: an alert appears before a failure, the planner acts, downtime is avoided.
- Looks professional: consistent design, clear states, no raw tracebacks.

**Non-goals:** user accounts/roles, mobile-first layout, real-time websockets, custom JavaScript components.

**Why Streamlit:** the hackathon recommends Streamlit generation through CoCo; it can run inside Snowflake; it needs no API layer; the backend switch keeps Phase 2 to a config change.

---

## 2. Architecture

```
┌────────────────────────────── Streamlit app (app/) ─────────────────────────────┐
│  pages/  (views only: layout + interaction, zero SQL, zero pandas business logic)│
│     │ call                                                                        │
│  components/  (reusable widgets: KPI card, status chip, risk gauge, charts)      │
│     │ call                                                                        │
│  services/api.py   ← THE CONTRACT (typed, ServiceResult envelope, cached)        │
│     │ call                                                                        │
│  data_access/      (backend switch: local_duckdb.py | snowflake.py)              │
└───────────────┬───────────────────────────────────────┬──────────────────────────┘
                │ BACKEND=local                          │ BACKEND=snowflake
             DuckDB + local agent                 Snowflake tables + Cortex agent
```

**Folder structure**
```
app/
  streamlit_app.py          # entry: shell, sidebar, routing, theme
  .streamlit/config.toml    # theme tokens
  pages/
    1_Fleet_Command_Center.py
    2_Alert_Queue.py
    3_Asset_Drilldown.py
    4_Ask_PulseOps.py
    5_OEE_and_Impact.py
    6_Work_Orders.py
  components/               # kpi_card.py, status_chip.py, charts.py, empty_state.py, error_banner.py
  services/
    contracts.py            # dataclasses/Pydantic models + enums (section 4)
    api.py                  # the public functions (section 4)
    normalize.py            # column/type normalisation (section 5)
    cache.py                # ttl and invalidation helpers
  data_access/              # backends (from PRD 1)
  config.yaml               # risk bands, display tz, thresholds, impact factor
tests/
  contract/                 # run on both backends
  ui/                       # Streamlit AppTest smoke tests
```

---

## 3. Required changes to PRD 1 (so backend and UI line up)

Apply these in the backend build; they are the root causes of most integration bugs.

| # | Change | Why |
|---|---|---|
| 1 | **All column names lowercase snake_case at the service boundary.** | Snowflake returns unquoted identifiers in UPPERCASE; DuckDB keeps your case. Normalising once in `normalize.py` removes a whole class of bugs. |
| 2 | **All timestamps stored and returned as UTC (timezone-aware). Display in `Asia/Kolkata`** (configurable `display_tz`). | Mixed naive/aware datetimes break charts, comparisons, and "stale data" logic. |
| 3 | **Add a global `as_of_ts` (the "replay clock").** Every time-dependent service function accepts `as_of_ts` and ignores data after it. Default = latest timestamp in the dataset, **not** wall-clock now. | The data is synthetic and in the past; "now" would make everything look stale. It also enables the scrub-through-time demo (section 9, improvement 1). |
| 4 | **Risk bands live in `config.yaml`** and are read by both ML/alert code and UI: HEALTHY < 0.30, WATCH 0.30–0.60, AT_RISK 0.60–0.80, CRITICAL ≥ 0.80. | Prevents the UI and alert logic from disagreeing on what "critical" means. |
| 5 | **Add `priority_score`** to alerts: `risk_score × (criticality/5) × (downtime_cost_per_hr_inr / max_downtime_cost_per_hr_inr) × 100`. | The queue order must be computed once, in the backend, and shown identically everywhere. |
| 6 | **Agent returns a structured response** (section 4.3), not a plain string. | The UI needs sources, SQL, confidence, and warnings as separate fields to render evidence and guardrails. |
| 7 | **`top_signals` is a list of `{signal, direction, contribution}`** (JSON). On Snowflake it arrives as VARIANT/string; normalise to a Python list. | Explainability display depends on it. |
| 8 | **Mutations (ack/dismiss/approve) are idempotent** and return the updated record. | Streamlit reruns the script often; double submits must not create duplicate work orders. |
| 9 | **Add `get_data_freshness()`** and a way to **simulate a sensor outage** (config flag). | Demonstrates the stale-data guardrail on demand. |

---

## 4. The contract (`services/contracts.py` and `services/api.py`)

### 4.1 Conventions (apply to every function)

| Topic | Rule |
|---|---|
| Return type | `ServiceResult[T]` = `{ok: bool, data: T \| None, error: {code, message, detail} \| None, meta: {backend, latency_ms, cached, as_of_ts}}` |
| Raising | Never raise to the UI. Catch, log, return `ok=False` with an error code. |
| Error codes | `BACKEND_UNAVAILABLE`, `QUERY_FAILED`, `NOT_FOUND`, `VALIDATION_ERROR`, `STALE_DATA`, `AGENT_ERROR`, `TIMEOUT`, `PERMISSION_DENIED` |
| DataFrames | Columns exactly as listed; lowercase; stable order; empty result = DataFrame with the columns and zero rows (never `None`) |
| IDs | strings (`asset_id="PUMP-03"`), never ints |
| Numbers | `float` / `int` (convert Decimal); percentages as 0–1 floats (UI formats as %); money in INR as float; durations in hours unless the name says `_minutes` |
| Time | tz-aware UTC `datetime`; `as_of_ts` optional on every time-dependent function (default = dataset latest) |
| Enums | uppercase strings exactly as below |

### 4.2 Functions

**Shared enums:** `HealthStatus = HEALTHY | WATCH | AT_RISK | CRITICAL` · `AlertStatus = OPEN | ACK | ACTIONED | DISMISSED` · `OrderType = PREVENTIVE | CORRECTIVE | EMERGENCY` · `FailureMode = BEARING_WEAR | MISALIGNMENT | OVERHEATING | MOTOR_WINDING`

| Function | Inputs | Returns (`data`) | Used by |
|---|---|---|---|
| `get_backend_info()` | – | `{backend: "local"\|"snowflake", warehouse?, as_of_default}` | Sidebar badge |
| `get_data_freshness(as_of_ts=None)` | as_of_ts | `{latest_reading_ts, minutes_stale, is_stale, threshold_minutes}` | Sidebar, banners, agent warning |
| `get_filters()` | – | `{plants: [{plant_id, plant_name}], lines: [...], asset_types: [...], min_ts, max_ts}` | Sidebar filters |
| `get_fleet_kpis(period_days=7, plant_id=None, as_of_ts=None)` | | `FleetKPIs` (below) | Page 1 |
| `get_asset_health(plant_id=None, as_of_ts=None)` | | DataFrame: `asset_id, asset_name, plant_id, line_id, asset_type, criticality, risk_score, health_status, oee_7d, last_reading_ts, open_alerts` | Page 1 heatmap |
| `get_alerts(status=None, plant_id=None, min_risk=0.0, limit=200, as_of_ts=None)` | | DataFrame: `alert_id, asset_id, asset_name, plant_id, line_id, asset_type, criticality, created_ts, risk_score, health_status, priority_score, predicted_failure_mode, predicted_window_hrs, top_signals, status, downtime_cost_per_hr_inr` (sorted by `priority_score` desc) | Page 2 |
| `update_alert_status(alert_id, status, actor)` | | updated alert row (dict) | Page 2/3 |
| `get_asset_detail(asset_id, as_of_ts=None)` | | `AssetDetail` (below) | Page 3 |
| `get_sensor_series(asset_id, start_ts, end_ts, resample="15min", as_of_ts=None)` | | DataFrame: `ts, vibration_mm_s, temperature_c, rpm, motor_current_a, risk_score` (max ~2,000 rows; resample server-side) | Page 3 charts |
| `get_asset_orders(asset_id, limit=5)` | | DataFrame: `order_id, order_type, source, status, created_ts, completed_ts, failure_mode, parts_used, cost_inr, technician_notes` | Page 3 |
| `get_spare_parts(asset_id)` | | DataFrame: `part_id, part_name, qty_on_hand, lead_time_days, unit_cost_inr` | Page 3, drafts |
| `get_related_docs(asset_id=None, failure_mode=None, limit=5)` | | DataFrame: `doc_id, title, doc_type, snippet` | Page 3, chat |
| `get_oee_trend(group_by="plant"\|"line"\|"asset"\|"fleet", period_days=30, granularity="day"\|"week", as_of_ts=None)` | | DataFrame: `period_start, group_id, group_name, availability, performance, quality, oee` | Page 5 |
| `get_impact_summary(planned_fix_factor=None, as_of_ts=None)` | | `ImpactSummary` (below) + DataFrame `events` | Page 5, KPI strip |
| `ask_agent(question, session_id, context=None, as_of_ts=None)` | `context` e.g. `{asset_id, alert_id}` | `AgentResponse` (4.3) | Page 4, Page 3 |
| `draft_work_order(alert_id)` | | `WorkOrderDraft` (4.4) | Page 2/3 dialog |
| `approve_work_order(draft, approver, idempotency_key)` | | `WorkOrderResult` (4.4) | Dialog |
| `list_work_orders(source=None, limit=100)` | | DataFrame: `order_id, asset_id, order_type, source, status, created_ts, approved_by, approved_ts, risk_score_at_draft, estimated_cost_avoided_inr` | Page 6 |

**Key models**

`FleetKPIs`: `fleet_oee, oee_delta_pp, open_alerts, critical_alerts, assets_at_risk, downtime_hours, downtime_cost_inr, failures_avoided, period_days, as_of_ts`

`AssetDetail`: `asset (static fields), current_risk_score, health_status, predicted_failure_mode, predicted_window_start, predicted_window_end, confidence ("high"|"medium"|"low"), top_signals (list), why_flagged (plain-English string), open_alert_id (nullable), oee_7d, mtbf_hours, mttr_hours, last_reading_ts`

`ImpactSummary`: `downtime_avoided_hours, oee_uplift_pp, cost_saved_inr, failures_total, failures_caught, median_lead_time_hours, false_alarms_per_week, assumptions: {planned_fix_factor, alert_threshold, lead_time_min_hours}`

### 4.3 `AgentResponse`

| Field | Type | UI behaviour |
|---|---|---|
| `answer_markdown` | str | Main answer bubble |
| `sources` | list of `{type: "document"\|"table"\|"metric", title, id}` | Rendered as citation chips under the answer |
| `sql_used` | list[str] | In an "Evidence" expander, read-only code block |
| `confidence` | `"high"\|"medium"\|"low"` | Badge next to the answer; low shows a caution note |
| `warnings` | list[str] | Amber banner (e.g. stale data) |
| `refused` | bool | If true, render as a polite "can't help with that" card with `refusal_reason` |
| `refusal_reason` | str\|None | |
| `suggested_actions` | list of `{type: "create_work_order"\|"open_asset", asset_id, alert_id?, label}` | Rendered as buttons under the answer |
| `follow_ups` | list[str] | 2–3 clickable suggested questions |
| `latency_ms` | int | Small footer |

**Why structured:** a plain-string agent forces the UI to guess where evidence, warnings, and actions are. Structured output is also what makes judges see "governed behaviour" (citations, confidence, guardrails).

### 4.4 Work-order models

`WorkOrderDraft`: `draft_id, alert_id, asset_id, asset_name, suspected_failure_mode, recommended_action, parts: [{part_id, part_name, qty_needed, qty_on_hand, lead_time_days, available}], proposed_window_start, proposed_window_end, estimated_labor_hours, estimated_cost_inr, estimated_cost_avoided_inr, risk_score_at_draft, rationale, created_ts`

`WorkOrderResult`: `order_id, status, approved_by, approved_ts, audit_id, already_existed (bool)`

`idempotency_key` = `f"{alert_id}:{hash(draft fields)}"`. If the same key is submitted twice, return the original result with `already_existed=true`. This protects against Streamlit reruns and double clicks.

---

## 5. Integration pitfalls and how the contract handles them

| Pitfall | Handling |
|---|---|
| Snowflake uppercase columns | `normalize.py` lowercases all column names |
| `Decimal`, `numpy` types | Convert to `float`/`int` in `normalize.py` |
| Timestamp types (`TIMESTAMP_NTZ/LTZ/TZ`) | Convert to tz-aware UTC; display via `display_tz` |
| VARIANT/JSON columns (`top_signals`) | Parse into Python lists/dicts; invalid JSON → empty list, never crash |
| Cold warehouse (first Snowflake query is slow) | Show spinner with "Waking the warehouse…" if a call exceeds 2 s; 30 s timeout → `TIMEOUT` |
| Credits | Cache reads (section 7); no auto-refresh on Snowflake by default |
| Large result sets | Hard `limit`; sensor series resampled in SQL, max ~2,000 rows |
| Streamlit reruns | Idempotent mutations; widget keys; guard buttons with `session_state` flags |
| Agent timeouts/errors | Return `AgentResponse` with `warnings` and `confidence="low"` or `ok=False` with `AGENT_ERROR`; UI shows retry |
| "Now" vs historical data | Use `as_of_ts` default = dataset latest |

---

## 6. Pages (what, why, how)

For every page: **Why** (the user need), **What** (contents), **Data** (contract calls), **States** (loading/empty/error), **Done when**.

### 6.0 App shell (`streamlit_app.py`, sidebar)
- **Why:** global context (which plant, which moment, which backend, is data fresh) must be visible on every page.
- **What:** product name + short tagline; plant filter; period selector (7/14/30 days); **Replay clock** control (see improvement 1); backend badge (`LOCAL` / `SNOWFLAKE`); data freshness pill (green "Live", amber "Stale 45 min"); link to Work Orders; "Reset demo" button.
- **Data:** `get_backend_info`, `get_data_freshness`, `get_filters`.
- **Behaviour:** filters stored in `st.session_state` (`plant_id`, `period_days`, `as_of_ts`); every page reads them; selections sync to URL query params so views are shareable.
- **States:** if `get_backend_info` fails → full-width error banner "Can't reach the data backend" with a Retry button; pages do not render data calls.

### 6.1 Page 1 — Fleet Command Center
- **Why:** the 5-second answer to "is the plant OK and what needs attention?"
- **What:** KPI strip (Fleet OEE with delta, Open alerts with critical count, Downtime cost, Failures avoided); **health heatmap** (rows = plants/lines, cells = assets coloured by `health_status` with icon + text, not colour alone); "Top 5 at-risk assets" list with risk, predicted window, and an "Investigate" button (deep-links to Page 3); small OEE sparkline.
- **Data:** `get_fleet_kpis`, `get_asset_health`, `get_alerts(limit=5)`.
- **States:** skeleton placeholders while loading; if no alerts → positive empty state ("No assets at elevated risk"); error → inline banner, rest of page still renders.
- **Done when:** all KPIs match the backend golden values; clicking an asset opens Page 3 with the asset preselected.

### 6.2 Page 2 — Alert Queue
- **Why:** triage. The planner needs a ranked, actionable list, not a log.
- **What:** table ranked by `priority_score`; columns: asset, plant/line, risk (with status chip), predicted failure mode, window (e.g. "in ~36 h"), top signal, status; filters (status, plant, min risk); row actions: **Investigate**, **Acknowledge**, **Dismiss**, **Create work order**; bulk Acknowledge.
- **Data:** `get_alerts`, `update_alert_status`, `draft_work_order`.
- **States:** empty queue message; failed update → toast with reason and row unchanged; optimistic UI not required.
- **Done when:** status changes persist after refresh; dismissed alerts hide from the default view; an alert can go from OPEN to work order in two clicks.

### 6.3 Page 3 — Asset Drill-down
- **Why:** trust and root cause. A prediction without evidence will not be acted on.
- **What:** header (asset name, type, plant/line, criticality, status chip, risk gauge); **four sensor charts** (vibration, temperature, RPM, current) sharing a time axis, with the **predicted failure window shaded** and the replay-clock line; "Why flagged" panel in plain English plus top-signal bars; last 5 maintenance orders; spare-part availability; related documents with titles; embedded **"Ask about this asset"** chat (pre-filled context); **Create work order** button.
- **Data:** `get_asset_detail`, `get_sensor_series`, `get_asset_orders`, `get_spare_parts`, `get_related_docs`, `ask_agent(context={asset_id})`.
- **States:** unknown `asset_id` in URL → "Asset not found" with link back; missing sensor data → chart gap with note (no interpolation lies).
- **Done when:** for a known failing asset, the shaded window precedes the failure and the explanation names the right failure mode.

### 6.4 Page 4 — Ask PulseOps (chat)
- **Why:** root-cause investigation in natural language is a required feature, and the place judges see governance.
- **What:** chat with history; every answer shows citation chips, confidence badge, Evidence expander (SQL/tables used), warning banner when relevant, suggested-action buttons, and 2–3 follow-up chips; example-question starter chips; a "clear conversation" button.
- **Data:** `ask_agent`, `get_related_docs` (for chip previews).
- **Behaviour:** `session_id` per browser session; the question is sent with the current `as_of_ts` and optional asset context; spinner shows steps ("Querying metrics… Searching documents…") if the backend provides them, else a generic spinner; refusals render as a calm card, not an error.
- **States:** agent error → message with Retry; empty state shows starter questions.
- **Done when:** all questions in `tests/agent_questions.yaml` render correctly (answer, sources, refusal, stale warning) with no UI errors.

### 6.5 Page 5 — OEE & Impact
- **Why:** proves business value, which is the Real-World Relevance score.
- **What:** OEE trend with Availability/Performance/Quality breakdown, switchable by fleet/plant/line/asset; **Impact panel**: baseline vs with-PulseOps (downtime avoided, OEE uplift in percentage points, ₹ saved), model quality card (failures caught, median lead time, false alarms/week); an **assumptions box** with an adjustable `planned_fix_factor` slider (default 0.4) that recomputes live; table of failure events (caught / missed, lead time).
- **Data:** `get_oee_trend`, `get_impact_summary`.
- **States:** if a slider recompute fails, keep the previous values and show a warning.
- **Done when:** changing the slider changes ₹ saved sensibly and the assumptions are always visible.

### 6.6 Page 6 — Work Orders
- **Why:** accountability. Humans approved these, and there is an audit trail.
- **What:** table of PulseOps-sourced orders (order id, asset, approver, time, risk at draft, cost avoided); filter by source; detail view; "Export CSV" button.
- **Data:** `list_work_orders`.
- **Done when:** an order approved on Page 2/3 appears here within one refresh.

### 6.7 Work-order dialog (modal used from Pages 2, 3, 4)
- **Why:** human-in-the-loop is a core guardrail; the draft must be reviewable and editable.
- **What:** `st.dialog` showing the draft: asset, suspected failure mode, recommended action (editable), proposed window (editable), parts with availability badges (red if not available, shows lead time), cost vs cost avoided, rationale, risk score at draft time; required "Approver name" field; buttons **Approve & create** / **Cancel**.
- **Behaviour:** approve is disabled until approver is filled; on click, disable button, call `approve_work_order` with the idempotency key, then show a success card with order id and a link to Page 6; on failure show the error and re-enable.
- **Done when:** double-clicking Approve creates exactly one order.

---

## 7. State, caching, performance

**`st.session_state` keys (single list; do not invent others without adding here):** `plant_id, period_days, as_of_ts, selected_asset_id, selected_alert_id, chat_messages, chat_session_id, draft, approve_in_flight, last_toast, demo_outage_enabled`.

**Caching (`st.cache_data` with TTL):**

| Data | TTL | Invalidate on |
|---|---|---|
| filters, backend info | 10 min | never |
| KPIs, asset health, OEE trend | 60 s | alert update, work order approval |
| alerts | 15 s | alert update, work order approval |
| sensor series, orders, docs, parts | 120 s | – |
| agent answers | no cache | – |

Cache keys include `as_of_ts`, `plant_id`, and `backend`. Mutations call `cache.invalidate(...)`.

**Performance targets:** page render under 3 s on local; sensor charts ≤ 2,000 points; no unbounded queries; **auto-refresh is OFF by default** and, when on, uses `st.fragment` with a 30 s interval (never auto-on for Snowflake because of credits).

---

## 8. Design system (consistent, restrained, readable)

**Tokens (`config.toml` + `components/theme.py`):**
- Light and dark themes both supported; one accent colour (deep teal or blue); neutral greys.
- **Status colours** with icon + label, never colour alone: HEALTHY (green, ✓), WATCH (yellow, ●), AT_RISK (orange, ▲), CRITICAL (red, ✖).
- Typography: system sans; page title 28, section 20, body 14–16; monospace only for SQL/IDs.
- Spacing scale 4/8/16/24; consistent card padding; max content width on wide screens.
- Charts: one library for all charts (Plotly) so shading and hover behave the same; consistent colours per sensor across pages; units on axes; no 3D, no gratuitous animation.

**Accessibility and clarity:** contrast ≥ 4.5:1 for text; every status has text; tooltips explain metrics (OEE, MTBF, MTTR) in one line; numbers formatted consistently (₹ with Indian grouping e.g. ₹12,34,500; percentages to 1 decimal; hours to 1 decimal); dates in `display_tz` with the timezone label shown once.

**Required states for every component:** loading (skeleton/spinner), empty (explains why and what to do), error (human message + Retry), partial (some panels failed, others fine).

**Copy rules:** plain language ("Bearing wear likely in ~36 h"), no jargon without a tooltip, no raw exceptions, no emojis in data tables.

---

## 9. Improvements included in this PRD (beyond PRD 1)

1. **Replay clock (as-of time travel).** A slider/scrubber in the sidebar sets `as_of_ts`. Move it back to before a failure and the alert queue, risk, and charts show only what was known then; move forward and watch the alert appear, then the failure. This turns a static dashboard into a demo story. *Backend cost: every function filters on `as_of_ts` (already in the contract).*
2. **Contract-first service layer with a result envelope.** Fewer integration bugs, clean error states, identical behaviour on both backends.
3. **Explainability everywhere.** Top-signal bars, plain-English "why flagged", and confidence badges instead of a bare score.
4. **Deep links.** `?page=asset&asset=PUMP-03&as_of=…` so every view can be opened directly (useful in the demo and in Slack/Jira messages later).
5. **Idempotent, approval-gated actions.** One order per approval, with an audit trail.
6. **Structured agent responses.** Citations, SQL, confidence, warnings, refusals, and suggested actions are rendered as UI, which makes the guardrails visible to judges.
7. **Stale-data and outage simulation.** A "Simulate sensor outage" toggle in the demo menu shows the agent and UI warning and refusing to state "current status". Proves fail-safe behaviour on demand.
8. **Shift handover brief (P1).** A button on Page 1 that asks the agent for a short summary (open critical alerts, actions taken, risks for the next 24 h); copy-to-clipboard. High real-world relevance, cheap to build on `ask_agent`.
9. **Alert hygiene (P1).** Snooze for N hours, de-duplication of repeated alerts for the same asset/failure mode.
10. **Demo mode (P0).** A "Demo" section in the sidebar: *Reset demo*, *Jump to failure story* (sets `as_of_ts` to 48 h before a chosen failure and opens the right asset), *Simulate outage*.
11. **Export (P1).** CSV for work orders and alerts; printable work-order summary.
12. **Self-check page (P1, tiny).** Hidden "System" section showing backend, row counts, latest data timestamp, contract test status. Helps CoCo in Phase 2 confirm parity.

**Priority for a one-day build:** P0 = everything in sections 4–8 except items marked P1, plus improvements 1–7 and 10. If time runs short, cut in this order: 12 → 11 → 9 → 8 → Page 6 detail view. Never cut the contract, the replay clock, the work-order dialog, or the empty/error states.

---

## 10. Testing the connection (so it does not break in Phase 2)

1. **Contract tests (`tests/contract/`)** — for every function in 4.2: returns `ServiceResult`; on success returns exactly the declared columns and dtypes; empty results keep columns; unknown id → `NOT_FOUND`; invalid input → `VALIDATION_ERROR`; `as_of_ts` in the past hides later data. **Same tests run with `BACKEND=local` and `BACKEND=snowflake`.** Phase 2 passes only when both pass.
2. **UI smoke tests (`tests/ui/`)** — Streamlit `AppTest` loads each page with default session state and with an injected failing service; asserts no exception and that an error banner appears when the service fails.
3. **Idempotency test** — call `approve_work_order` twice with the same key; exactly one record exists.
4. **Golden check** — Page 1 KPIs and Page 5 OEE equal `golden_values.json` within tolerance.
5. **Manual demo walk-through** — follow `DEMO.md` end to end on a fresh session; no console errors, no raw tracebacks.

---

## 11. Frontend build order (checkpoint after each step)

1. `config.yaml`, `contracts.py`, `normalize.py`, `cache.py`, `ServiceResult` helper.
2. `services/api.py` implemented over the **local** backend; contract tests green.
3. Theme, shell/sidebar, replay clock, filters, freshness pill, backend badge.
4. Components: KPI card, status chip, risk gauge, sensor chart (with shaded window), citation chip, empty/error/skeleton.
5. Page 1 → Page 2 → work-order dialog → Page 3.
6. Page 4 (chat) wired to `ask_agent`, including refusal and warning rendering.
7. Page 5 (impact) with live slider; Page 6.
8. Demo mode (jump to story, simulate outage, reset), deep links.
9. UI smoke tests, golden check, polish pass (spacing, copy, states).
10. Write `FRONTEND_HANDOFF.md` for Phase 2: list of every service function, its Snowflake query source, known differences, and the `BACKEND=snowflake` run command.

## 12. Acceptance criteria

- [ ] Pages contain no SQL and no direct backend imports (grep check)
- [ ] All service functions match section 4 on the local backend; contract tests pass
- [ ] Fresh clone: `make run` shows a working app with data
- [ ] Alert → drill-down → ask "why?" → approve order works in under 2 minutes, and the order appears on Page 6
- [ ] Replay clock shows an alert appearing before a failure for at least one asset
- [ ] Stale-data simulation produces a visible warning and the agent declines current-status claims
- [ ] Double-clicking Approve creates one order
- [ ] No raw tracebacks anywhere; every component has loading/empty/error states
- [ ] Backend badge and freshness pill correct on both backends
- [ ] `FRONTEND_HANDOFF.md` exists for PRD 2

## 13. Notes for PRD 2 (CoCo)
When switching to Snowflake, only `data_access/snowflake.py` and the SQL it runs should change. If a page needs editing, the contract was violated: fix the service layer instead. Run the contract tests with `BACKEND=snowflake` before opening the UI.
