# Bug Regression — Decision Gate

| | |
|---|---|
| **目标** | 选择回归路径并记录依据 |
| **输入** | Coverage Match、影响分析、覆盖缺口 |
| **产出** | `notes[]`: `decision_path:` + 决策理由 |

**Skills:** `test-case-design`, `automation`

**Paths:** `execute_existing` | `supplement_cases` | `generate_automation` | `no_executable_regression`

**Gate:** 未记录 `decision_path:` 前，不进入 Regression Plan。

**Machine:** `decision_path:` — `tools/stage_gate.py`

**Prev → Next:** Coverage Match → Regression Plan
