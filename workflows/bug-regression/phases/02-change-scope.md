# Bug Regression — Change Scope

| | |
|---|---|
| **目标** | 确定代码/配置/数据实际改了什么 |
| **输入** | Bug Intake、修复来源、Project Profile product repositories |
| **产出** | `change_scope` 产物；变更文件/组件；根因证据（`known`/`unknown`/`not_required`） |

**Skills:** `test-analysis` — read `skills/test-analysis/references/bug-regression-rules.md`

**Repository:** Project Profile product repositories

**Knowledge:** 术语、领域规则、历史教训（与 bug 区域相关）

**Gate:** 未记录具体变更文件/commit/配置前，不进入 Impact Analysis。

**Machine:** artifact `change_scope`; repository evidence — `tools/stage_gate.py`

**Prev → Next:** Bug Intake → Impact Analysis
