# Shop Platform：15 分钟上手

本指南使用仓库内的 `shop-platform` 示例说明 Agent-next 的交互方式。它的目标是让
用户先看清已有输入、缺少什么以及下一步会产生什么，再让 Agent 读取对应 Skill 并完成
内容分析。CLI 不会替用户臆造需求、执行共享环境操作或写入外部平台。

## 1. 先确认项目可用

```bash
agent-next doctor --project examples/shop-platform/project.yaml
agent-next inventory --project examples/shop-platform/project.yaml
```

`inventory` 显示每个输入的状态、版本和失效原因。示例中的 `PRD-checkout-001` 是一个
已就绪 PRD；产物 ID 加 `@revision` 后才能作为下游来源，例如 `PRD-checkout-001@1`。

## 2. 从 PRD 规划功能测试

```bash
agent-next plan \
  --project examples/shop-platform/project.yaml \
  --workflow feature-quality \
  --scope checkout \
  --goal test_cases
```

输出依次列出 Intake、需求说明、风险分析、测试点和测试用例。`--workflow` 只接受 Workflow Pack
名称；功能工作流唯一名称为 `feature-quality`，不提供旧名称或 alias。

先完成无产物的 Intake Gate：

```bash
agent-next run \
  --project examples/shop-platform/project.yaml \
  --workflow feature-quality \
  --capability feature-intake \
  --run-id checkout-requirement \
  --track backend

agent-next record \
  --run-id checkout-requirement \
  --knowledge-plan-status not_needed \
  --knowledge-plan-summary "当前项目知识足够" \
  --knowledge-used path=skills/requirement-analysis/references/intake-sources.md,purpose=intake \
  --note intake_input:PRD-checkout-001

agent-next gate \
  --project examples/shop-platform/project.yaml \
  --run-id checkout-requirement
```

Intake 通过后，在同一 Run State 中准备并创建第一个产物：

```bash
agent-next run \
  --project examples/shop-platform/project.yaml \
  --workflow feature-quality \
  --capability requirement-specification \
  --run-id checkout-requirement \
  --track backend

agent-next scaffold \
  --project examples/shop-platform/project.yaml \
  --workflow feature-quality \
  --capability requirement-specification \
  --scope checkout \
  --artifact-id REQ-checkout-001 \
  --source-artifact PRD-checkout-001@1 \
  --run-id checkout-requirement \
  --track backend
```

随后由 Agent 按该阶段的 Skill 补充内容和运行证据；用 `status`、`explain` 查看当前阻塞，
用 `gate --mark-ready` 仅在证据、前置产物和内容校验都通过后标记就绪。未填写的原始
模板、残留占位符以及 Gate 后被修改的 ready 产物都会被阻止或标记为 stale。

## 3. 登记已有的外部输入

Release 基线、既有 PRD、需求单导出等并不是 Agent-next 生成的内容。将已存在的本地文件
登记为库存输入，而不是复制或改写它：

```bash
agent-next register \
  --project examples/shop-platform/project.yaml \
  --artifact-id BASELINE-checkout-001 \
  --type release_baseline \
  --scope checkout-release \
  --content examples/shop-platform/docs/checkout-release-baseline.md \
  --track web --track backend \
  --ready
```

`register` 只在 `runs/<run-id>/artifacts/` 下创建元数据记录，文件本体必须已在仓库内。
默认登记为 `draft`；`--ready` 是用户显式确认该输入可供下游使用的边界。它不会进行
远程写入，也不会向 `outputs/` 增加追溯文件。

如果先以 draft 登记，可在本地复核后显式晋级：

```bash
agent-next gate \
  --project examples/shop-platform/project.yaml \
  --artifact-id BASELINE-checkout-001 \
  --mark-ready
```

## 4. 规划 Release 验收

```bash
agent-next plan \
  --project examples/shop-platform/project.yaml \
  --workflow release-acceptance \
  --scope checkout-release \
  --goal acceptance_report
```

在只有 Release 基线时，计划会生成：

```text
release_scope → acceptance_plan → execution_record → acceptance_report
```

如果需求说明、风险分析、测试用例来自其他 scope，计划会将其列为 optional missing；是否
纳入由 Release 负责人决定，并在验收计划的范围对账和覆盖缺口中记录。测试管理平台同步
仍由相应 Skill 调用既有 CLI 完成，不由 Core 重写平台客户端。

## 5. 阅读结果与下一步

- `agent-next status --run-id <run-id>`：显示当前阶段和 Gate blocker。
- `agent-next explain --run-id <run-id>`：显示该阶段所需 Skill、产物和阻塞原因。
- `examples/shop-platform/release-acceptance/`：查看计划、执行记录和报告如何共同表达
  “通过的范围”与“未接受的覆盖缺口”。

当命令显示 `BLOCKED`，先按输出补齐缺失输入或证据；不要把 blocker 当作可绕过的警告。
