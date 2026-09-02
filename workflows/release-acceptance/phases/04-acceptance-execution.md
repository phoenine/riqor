# Release Acceptance — Acceptance Execution

| | |
|---|---|
| **目标** | 执行已确认的验收动作并收集证据 |
| **输入** | Acceptance Plan、验收覆盖映射、环境、Project Profile automation repositories |
| **产出** | API/Web 自动化执行计划与结果；`execution_record` 或 `execution_evidence:` / `data_injection:`；测试管理平台验收单/用例关联证据 |

**Skills:** `automation`, `release-acceptance`; load only the project-specific automation or data-preparation Skills selected by the Project Profile.

**Confirmation before:** full automation, data injection, external platform writes, SSH, environment changes.

**Gate:** Acceptance Execution must actively route automation before Release Decision:

- API coverage -> the Profile automation repository with API capability.
- Web/UI or hybrid coverage -> the Profile automation repository with Web capability.
- Record `automation_execution_plan:` with selected cases, repositories,
  branches, target environment, commands, and report/artifact paths before or
  with execution evidence.
- If API or Web automation cannot run, record `automation_execution_skip:` with
  the exact reason, impact, and required follow-up. Do not silently replace it
  with manual evidence.

须有执行证据与问题分类后再做 Release Decision。若创建或更新 测试管理平台验收单，必须记录确认、外部单号、关联的既有测试用例，以及执行证据回填结果。

**Machine:** `automation_execution_plan:` or `automation_execution_skip:` plus
`execution_record` or `execution_evidence:` / `data_injection:` / skip —
`tools/stage_gate.py`

**Prev → Next:** Acceptance Plan → Release Decision
