# Feature Testing — Optional Case Sync Or Generation

| | |
|---|---|
| **目标** | 同步项目选择的测试管理平台或生成自动化草案（可选） |
| **输入** | 已确认的测试设计与用例 |
| **产出** | `external_sync:` 结果、`automation_classification` 和/或 `automation_implementation`；或 skip |

**Skills:** Project Profile 选择的 integration Skill（例如 `zentao-sync`）、`automation`，以及 Project Profile 选择的实现 Skill（例如 `pytest-yaml-api`）

**Confirmation before:** 外部平台写入、自动化仓库文件变更。

**Gate:** 本阶段不执行用例。生成自动化后必须静态校验 case contract 与
REQ/RISK/TP/TC/AUTO 追溯关系。

**Machine:** optional; automation classification/implementation or skip —
`tools/stage_gate.py`, `tools/traceability_lint.py`

**Prev → Next:** Test Design → Optional Case Execute
