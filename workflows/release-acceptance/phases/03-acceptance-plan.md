# Release Acceptance — Acceptance Plan

| | |
|---|---|
| **目标** | 制定 release bundle 验收计划、侧重点、性能关注与准入标准 |
| **输入** | Baseline、Resolved Scope、Scope Gap、现有自动化/手工用例 |
| **产出** | `acceptance_plan`；验收侧重点；性能与稳定性计划；阈值；阻塞项；执行计划 |

**Skills:** `release-acceptance`, `test-case-design`, `automation` — read `skills/test-case-design/references/test-case-design-methodology.md` and `skills/test-case-design/references/coverage-review-rules.md` when deriving or reviewing manual acceptance cases.

**Confirmation before:** automation execution, shared data mutation, or creating/updating test-management acceptance orders.

**Gate:** 计划必须引用已有 project-defined track 测试资产，避免复制用例；Priority 与 Risk 必须分离。阈值、阻塞项、性能/稳定性关注、测试管理平台验收单策略、回滚/恢复就绪（生产范围时）记录后再执行。

**Machine:** artifact `acceptance_plan` — `tools/stage_gate.py`

**Prev → Next:** Scope Collection → Acceptance Execution
