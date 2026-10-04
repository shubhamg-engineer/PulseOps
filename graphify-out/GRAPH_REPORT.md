# Graph Report - New folder  (2026-10-01)

## Corpus Check
- Corpus is ~1,691 words - fits in a single context window. You may not need a graph.

## Summary
- 17 nodes · 28 edges · 4 communities (3 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 1,691 input · 950 output

## Community Hubs (Navigation)
- Data Foundation & Physics
- ML Intelligence & Analytics
- Command Center & Root-Cause Agent
- Snowflake Deployment & Handoff

## God Nodes (most connected - your core abstractions)
1. `10-Step Execution Process` - 8 edges
2. `Unified Data Model` - 6 edges
3. `F2: ML Failure Prediction Model` - 5 edges
4. `F3: Streamlit Command Center UI` - 5 edges
5. `Synthetic Data Generator (P0)` - 4 edges
6. `F4: Root-Cause NL Agent` - 4 edges
7. `PRD 1: PulseOps Build Everything` - 3 edges
8. `PulseOps Command Center` - 3 edges
9. `OEE & Reliability Metrics` - 3 edges
10. `Snowflake Deployment Pack (/snowflake)` - 3 edges

## Surprising Connections (you probably didn't know these)
- `PRD 1: PulseOps Build Everything` --SPECIFIES--> `10-Step Execution Process`  [EXTRACTED]
  PRD_1_Antigravity_Build.md → PRD_1_Antigravity_Build.md  _Bridges community 0 → community 1_
- `Synthetic Data Generator (P0)` --POPULATES--> `Unified Data Model`  [EXTRACTED]
  PRD_1_Antigravity_Build.md → PRD_1_Antigravity_Build.md  _Bridges community 0 → community 2_
- `Unified Data Model` --CALCULATED_BY--> `OEE & Reliability Metrics`  [EXTRACTED]
  PRD_1_Antigravity_Build.md → PRD_1_Antigravity_Build.md  _Bridges community 2 → community 1_
- `Snowflake Deployment Pack (/snowflake)` --PACKAGES_INTO--> `PRD 2 Handoff Deliverables`  [EXTRACTED]
  PRD_1_Antigravity_Build.md → PRD_1_Antigravity_Build.md  _Bridges community 0 → community 3_
- `10-Step Execution Process` --EXECUTES_STEP_9_10--> `PRD 2 Handoff Deliverables`  [EXTRACTED]
  PRD_1_Antigravity_Build.md → PRD_1_Antigravity_Build.md  _Bridges community 3 → community 1_

## Communities (4 total, 1 thin omitted)

### Community 0 - "Data Foundation & Physics"
Cohesion: 0.33
Nodes (6): Failure Physics & Signatures, Core Ground Rules, PRD 1: PulseOps Build Everything, PulseOps Command Center, Snowflake Deployment Pack (/snowflake), Synthetic Data Generator (P0)

### Community 1 - "ML Intelligence & Analytics"
Cohesion: 0.70
Nodes (5): 10-Step Execution Process, F3: Streamlit Command Center UI, F2: ML Failure Prediction Model, OEE & Reliability Metrics, F6: OEE & Financial Impact Simulation

### Community 2 - "Command Center & Root-Cause Agent"
Cohesion: 0.67
Nodes (4): Unified Data Model, F1: Rolling Feature Engineering, F4: Root-Cause NL Agent, F5: Work-Order Automation

## Knowledge Gaps
- **3 isolated node(s):** `Snowflake CoCo (PRD 2)`, `Core Ground Rules`, `Failure Physics & Signatures`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `10-Step Execution Process` connect `ML Intelligence & Analytics` to `Data Foundation & Physics`, `Command Center & Root-Cause Agent`, `Snowflake Deployment & Handoff`?**
  _High betweenness centrality (0.524) - this node is a cross-community bridge._
- **Why does `Synthetic Data Generator (P0)` connect `Data Foundation & Physics` to `ML Intelligence & Analytics`, `Command Center & Root-Cause Agent`?**
  _High betweenness centrality (0.188) - this node is a cross-community bridge._
- **Why does `Unified Data Model` connect `Command Center & Root-Cause Agent` to `Data Foundation & Physics`, `ML Intelligence & Analytics`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **What connects `Snowflake CoCo (PRD 2)`, `Core Ground Rules`, `Failure Physics & Signatures` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._