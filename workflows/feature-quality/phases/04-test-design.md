# Feature Testing — Test Design

| | |
|---|---|
| **目标** | 将需求转为测试点与可执行用例 |
| **输入** | 需求规格、风险分析、现有覆盖（如有） |
| **产出** | `test_points` + `test_cases` 产物；覆盖缺口 |

**Skills:** `test-analysis`, `test-case-design` — read `skills/test-analysis/references/test-analysis-methodology.md`, `skills/test-case-design/references/test-case-design-methodology.md`, `skills/test-case-design/references/coverage-review-rules.md`, and `case-writing-rules.md`; record `analysis_depth` in `test_points`.

**Repository:** Project Profile product repositories; Project Profile automation repositories for automation inventory

**Gate:** 本阶段不写入测试管理平台、不跑自动化（须用户确认）。

**Machine:** artifacts `test_points`, `test_cases` — `tools/stage_gate.py`

**Prev → Next:** Risk Analysis → Optional Case Sync Or Generation
