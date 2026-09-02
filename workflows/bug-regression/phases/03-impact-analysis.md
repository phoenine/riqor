# Bug Regression — Impact Analysis

| | |
|---|---|
| **目标** | 判断可能影响的需求、共享组件与回归面 |
| **输入** | Change Scope、根因证据、知识库 |
| **产出** | `risk_analysis` 产物；影响域；回归风险列表；Coverage Scope Review |

**Skills:** `test-analysis` — read `skills/test-analysis/references/bug-regression-rules.md` and `skills/test-analysis/references/test-analysis-methodology.md` when defining regression coverage focus.

**Repository:** Project Profile product repositories (source-to-component mapping)

**Gate:** 未记录影响域、回归风险、Requirement / Risk / Condition / Test Point 连续性审查前，不进入 Coverage Match。

**Machine:** artifact `risk_analysis`; repository evidence — `tools/stage_gate.py`

**Prev → Next:** Change Scope → Coverage Match
