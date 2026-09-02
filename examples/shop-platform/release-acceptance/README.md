# Release 验收示例

本目录展示同一 Release 从计划、执行到决策报告的最小完整链路。示例中的项目、环境、
人员、需求与证据标识均为虚构数据；它们用于说明产物粒度和可追溯关系，不代表可直接
发布的结论。

- `acceptance-plan.md`：声明验收范围、退出标准和已知覆盖缺口。
- `execution-record.md`：记录实际执行结果，明确未执行范围不会被“通过数”掩盖。
- `acceptance-report.md`：聚合计划与执行证据，给出带条件的发布决策。

实际运行时，请通过 `python -m tools.agent_next scaffold` 创建对应 `.md` 产物；不要复制
本示例中的虚构 ID。机器追溯信息保存在 `runs/`，不写入交付正文。
