# Feature Testing — Optional Case Sync Or Generation

| | |
|---|---|
| **目标** | 同步项目选择的测试管理平台或生成自动化草案（可选） |
| **输入** | 已确认的测试设计与用例 |
| **产出** | `external_sync:` 结果、`automation_classification` 和/或 `automation_implementation`；或 skip |

**Skills:** Project Profile 选择的 integration Skill（例如 `zentao-sync`）、`automation`，以及 Project Profile 选择的实现 Skill（例如 `pytest-yaml-api` 或 `pytest-playwright-web`）

**Confirmation before:** 外部平台写入、自动化仓库文件变更。

**Gate:** 本阶段不执行用例。生成自动化后必须静态校验 case contract 与
REQ/RISK/TP/TC/AUTO 追溯关系。

**Machine:** optional; automation classification/implementation or skip —
`tools/stage_gate.py`, `tools/traceability_lint.py`

当 `automation_classification` 包含 `A0/A1 + api/hybrid` 且 Project Profile
声明 API automation repository 时，运行：

```bash
python -m tools.agent_next prepare-automation \
  --project config/projects/<project-id>.yaml \
  --classification-artifact <classification-id> \
  --test-cases-artifact <test-cases-id> \
  --implementation-artifact <implementation-id> \
  --run-id <run-id>
```

两个输入 Artifact 必须已登记且为 `ready`；分类正文还会再次通过类型 Validator，且
符合条件行的 Destination 必须与 Profile 选中的仓库一致。命令通过所选 Skill 的
`provider.yaml` 创建薄 consumer 项目，默认执行锁定依赖安装，并在同一 Run State
登记 draft `automation_implementation`。初始化 Project Profile 本身不访问网络。
无符合条件的分类时明确输出 `SKIPPED` 并记录 skip note。

**Prev → Next:** Test Design → Optional Case Execute
