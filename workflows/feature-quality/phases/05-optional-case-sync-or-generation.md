# Feature Testing — Optional Case Sync Or Generation

| | |
|---|---|
| **目标** | 同步项目选择的测试管理平台或生成自动化草案（可选） |
| **输入** | 已确认的测试设计与用例 |
| **产出** | `external_sync:` 结果和/或 `automation_classification`；或 skip |

**Skills:** Project Profile 选择的 integration Skill（例如 `zentao-sync`）和/或 `automation`

**Confirmation before:** 外部平台写入、自动化仓库文件变更。

**Gate:** 本阶段不执行用例。

**Machine:** optional; automation classification or skip — `tools/stage_gate.py`

**Prev → Next:** Test Design → Optional Case Execute
