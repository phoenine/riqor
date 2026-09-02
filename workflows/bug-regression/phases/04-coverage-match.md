# Bug Regression — Coverage Match

| | |
|---|---|
| **目标** | 匹配现有手工/自动化覆盖与缺口 |
| **输入** | Impact Analysis、Project Profile automation repositories、Project Profile product repositories |
| **产出** | `coverage_match` 产物；原 bug/需求/风险/自动化覆盖与缺口 |

**Skills:** `test-case-design`, `automation` — read `skills/test-case-design/references/coverage-review-rules.md`, `skills/test-case-design/references/test-case-design-methodology.md`, and `case-writing-rules.md` before supplementing cases.

**Gate:** 未检索现有覆盖前，不新建用例。

**Machine:** artifact `coverage_match` — `tools/stage_gate.py`

**Prev → Next:** Impact Analysis → Decision Gate
