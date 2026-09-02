# Release Acceptance — Release Decision

| | |
|---|---|
| **目标** | 对照阈值评估结果并做发布判定 |
| **输入** | Plan、执行结果、测试管理平台验收单、问题列表、阈值与阻塞项 |
| **产出** | `acceptance_report`；`release_decision:`；跟进责任人 |

**Skills:** `release-acceptance`, `reporting`; Project Profile integration Skill when updating an external platform

**Decision:** `accepted` | `blocked` | `rejected` | `accepted_with_known_issues`

**Gate:** 已知问题须用户接受；生产发布须记录回滚/恢复就绪。报告必须能追溯到 release scope、底层测试资产、测试管理平台验收单（如创建）、执行证据和最终结论。

**Machine:** `release_decision:`; artifact `acceptance_report`; traceability — `tools/stage_gate.py`

**Prev → Next:** Acceptance Execution → Optional Post-release Observation
