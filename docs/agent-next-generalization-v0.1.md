# Agent-next 通用化 v0.1 设计文档

> 状态：Draft  
> 版本：v0.1  
> 日期：2026-09-01  
> 实现根目录：`/Users/phoenine/Documents/workbench/agent-new`

> 实现策略：以现有 Agent-next 为母版进行复用和参数化，不按本文重新实现一套平行引擎。

## 1. 文档目的

本文定义 Agent-next 作为通用、可开源、可适配不同项目的测试工程 Agent 平台所需的产品交互、核心模型、工作流契约和 v0.1 实现范围。

本设计重点解决以下问题：

1. 新项目没有知识库时，能够从统一模板可靠地初始化。
2. 用户可以从 PRD、需求文档、风险分析、测试点、测试用例、Bug 或 Release 中任意已有位置开始。
3. Agent-next 能识别已有资产、缺失依赖和可执行的下一步，而不是要求用户理解内部 workflow、phase、skill 和 gate。
4. 项目专属配置、知识和集成从 Core 中解耦，通过 Project Profile 与 Skill 扩展；Adapter 仅作为可选薄驱动。
5. 需求、风险、测试点、用例、自动化、执行和报告之间保持可审计的证据链。
6. 禅道写入、共享环境执行、数据修改等副作用操作仍然必须由用户显式确认。

## 2. 产品定位

Agent-next 的通用定位是：

> 用户提供当前已有材料和目标结果，Agent-next 自动盘点资产、规划依赖、补齐中间产物，并在任何外部写入或共享环境执行前请求确认。

Agent-next 不是单纯的文档生成器，也不是隐藏规则的一键测试机器人。它应当是一套以资产、证据和阶段门禁为核心的测试工程工作台。

## 3. 设计原则

### 3.1 目标驱动，而非阶段驱动

用户表达“我想生成测试用例”或“我要回归这个问题”，系统负责把目标解析为执行计划。用户不需要先选择内部阶段。

### 3.2 从任意成熟度开始

新任务不强制从 PRD 开始。系统先盘点已有资产，再决定复用、补齐、复核或失效重建。

### 3.3 硬依赖与软依赖分离

- 硬依赖缺失：当前能力不可执行，必须先补齐。
- 软依赖缺失：允许继续，但输出必须降低证据等级并显示缺口。

例如测试点设计必须有需求背景，但代码和完整风险分析可以是软依赖。

### 3.4 知识不是当前任务证据

知识库提供可复用背景；PRD、需求文档、代码、提交、执行日志和用户确认才是当前任务证据。系统不得用知识库内容冒充本次变更的事实证据。

### 3.5 产物必须可追溯

每个下游产物都应引用实际使用的上游资产、代码证据和生成版本。上游变化后，系统能够判断下游资产是否过期。

### 3.6 副作用默认关闭

本地读取、分析和生成可以自动进行；远端写入、共享环境执行、共享数据修改和部署类操作必须先展示计划并获得确认。

### 3.7 项目专属能力不进入 Core

具体产品、平台、仓库、分支和环境策略都应通过下游 Profile 或 Skill
扩展提供，不能成为 Core 的固定枚举或随通用仓库分发。已有 Skill 或 CLI
能完成集成时，不得为了形式统一重新实现 Adapter。

## 4. 总体架构

Agent-next 分为四层：

| 层级 | 主要职责 | 示例 |
|---|---|---|
| Core Engine | 资产、依赖、Planner、Run State、Gate、溯源、确认 | 通用 |
| Project Profile | 项目、Track、仓库、知识库、环境、策略 | 商城、数据平台 |
| Workflow Pack | Feature、Bug、Release 及项目自定义流程 | Feature Quality |
| Skills / Optional Adapters | Skill 编排现有 CLI、仓库和测试框架；仅在确有共享驱动需求时增加薄 Adapter | GitHub、GitLab、禅道、Playwright |

建议的实现目录：

```text
agent-new/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── config/
│   ├── agent-next.yaml
│   └── projects/
├── docs/
├── knowledge/
│   └── <project-id>/
├── workflows/
│   ├── feature-quality/
│   ├── bug-regression/
│   └── release-acceptance/
├── skills/
├── templates/
│   ├── artifacts/                 # *.md.tmpl managed artifact sources
│   └── knowledge/
├── schemas/
├── tools/
├── repositories/
│   ├── product/
│   ├── automation/
│   └── tools/
├── outputs/
│   └── <project-id>/
├── runs/
└── tests/
```

目录约束：通用 Core、CLI、校验器和状态工具直接放在 `tools/`；仓库不再维护
`src/agent_next/` Python 包目录。`templates/` 是知识库与产物模板的唯一来源；交付物
模板统一使用 `templates/artifacts/*.md.tmpl`，生成产物仍为 `.md`。
运行时不得再从代码包内维护第二份模板。

## 5. 核心领域模型

### 5.1 Project

Project 是所有配置、知识、仓库、运行和产物的一级隔离边界。

```yaml
project:
  id: shop-platform
  name: Shop Platform
  description: 电商交易平台
  tracks:
    - web
    - backend
    - mobile
  default_track: backend
```

`tracks` 是项目自定义标签，具体取值只存在于对应 Project Profile 中，不是
Core 枚举。

### 5.2 Resource

Resource 表示 Agent-next 可读取或操作的外部资源：

- 产品代码仓库
- 自动化仓库
- 测试数据工具仓库
- PRD 或需求文档源
- 需求和 Bug 管理平台
- 测试环境
- 报告发布目标

Resource 必须声明类型、位置、能力、Track 和访问策略。

### 5.3 Artifact

Artifact 是可版本化、可验证和可追溯的工作产物。

v0.1 支持以下标准类型：

- `prd`
- `requirement_spec`
- `requirement_review`
- `risk_analysis`
- `test_points`
- `test_cases`
- `automation_classification`
- `automation_implementation`
- `execution_record`
- `bug_report`
- `regression_plan`
- `regression_report`
- `acceptance_plan`
- `acceptance_report`
- `run_summary`

每个 Artifact 至少包含：

```yaml
id: TC-checkout-001
type: test_cases
project_id: shop-platform
scope_id: checkout
tracks: [web, backend]
status: ready
revision: 3
content_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
source_artifacts:
  - REQ-checkout-001@2
  - RISK-checkout-001@1
  - TP-checkout-001@2
evidence:
  - type: document
    reference: docs/checkout-prd.md
validation:
  status: passed
  checked_at: 2026-09-01T12:00:00+08:00
```

`scope_id` 是 Feature、Bug 或 Release 等一次工作范围的稳定标识。Inventory
可以展示整个 Project，但 Planner 必须在明确的 `project_id + scope_id` 内选择
同类型资产，避免把其他功能的需求或风险错误复用到当前目标。Release 产物仍可通过
`source_artifacts` 显式引用其他 scope 的资产。

### 5.4 Artifact 状态

统一使用以下状态：

| 状态 | 含义 |
|---|---|
| `missing` | 尚不存在 |
| `draft` | 已生成，但存在未解决缺口或尚未确认 |
| `ready` | 已通过当前类型的验证门禁 |
| `stale` | 上游资产发生变化，需要重新复核或生成 |
| `blocked` | 缺少硬依赖、权限或确认 |
| `failed` | 生成、验证或执行失败 |

### 5.5 Evidence

Evidence 用于支撑具体结论，标准类型包括：

- `document`
- `repository_file`
- `symbol`
- `commit`
- `diff`
- `api_contract`
- `runtime_observation`
- `execution_log`
- `user_confirmation`

证据必须记录引用位置和可选 revision。仅记录“读取过某个仓库”不足以支撑风险结论。

### 5.6 Capability

Capability 表示可以由系统执行的原子能力，例如“生成需求规格”“进行代码风险验证”“上传禅道”。

```yaml
id: test-case-design
title: 测试用例设计
requires:
  all:
    - requirement_spec
    - risk_analysis
    - test_points
optional:
  - product_repository
produces:
  - test_cases
side_effect: false
skill: test-case-design
```

Workflow 由 Capability 组成，不再由 Core 中的固定 Python 分支定义。

## 6. Project Profile

Project Profile 是通用化的关键配置入口。

建议配置示例：

```yaml
schema_version: 1

project:
  id: shop-platform
  name: Shop Platform
  tracks: [web, backend, mobile]
  default_track: backend

knowledge:
  root: knowledge/shop-platform
  template: standard-product
  index: knowledge/shop-platform/_index.md

repositories:
  product:
    - id: shop-web
      path: repositories/product/shop-web
      tracks: [web]
    - id: shop-service
      path: repositories/product/shop-service
      tracks: [backend]
  automation:
    - id: shop-api-test
      path: repositories/automation/shop-api-test
      capabilities: [api]
    - id: shop-web-test
      path: repositories/automation/shop-web-test
      capabilities: [web]

integrations:
  api_automation:
    skill: pytest-yaml-api
    config:
      runtime_url: https://github.com/phoenine/rigorpath_api_test.git
      runtime_revision: <immutable-tag-or-full-commit>
  requirement_tracker:
    skill: zentao-sync
  issue_tracker:
    skill: github-issues
  source_control:
    skill: gitlab-source

environments:
  local:
    risk: local
  test:
    risk: shared
  staging:
    risk: production_like

policies:
  require_confirmation:
    - remote_write
    - shared_environment_execution
    - shared_data_mutation
```

Profile 必须通过 JSON Schema 或等价机制验证。未知扩展字段应放在明确的 `extensions` 命名空间中，避免配置拼写错误被静默接受。

## 7. 知识库初始化与维护

### 7.1 标准知识库模板

```text
knowledge/<project-id>/
├── _index.md
├── glossary/
├── business-rules/
├── user-flows/
├── architecture/
├── interfaces/
├── data-model/
├── test-strategy/
├── operations/
└── _gaps.md
```

并非每个项目都必须填满所有目录。模板提供稳定的分类和入口，空目录不代表门禁失败。

### 7.2 通用知识页契约

```yaml
id: order-status
title: 订单状态
type: business_rule
domains: [order]
aliases: []
sources:
  - type: document
    reference: docs/prd/order.md
related:
  - path: knowledge/shop-platform/user-flows/create-order.md
    relation: participates_in
confidence: confirmed
last_verified: 2026-09-01
```

推荐的 `type` 包括：

- `index`
- `term`
- `business_rule`
- `user_flow`
- `architecture`
- `interface`
- `data_model`
- `test_strategy`
- `operation`
- `scenario`

Project Profile 可以扩展类型，但不得覆盖通用类型的语义。

### 7.3 空知识库启动流程

知识内容不是新项目的前置条件。`init` 自动创建内部空骨架，用户无需先理解、配置或
维护知识库；没有可用知识时，Workflow 记录 `knowledge_not_applicable:` 后继续。

`agent-next init` 应执行：

1. 创建 Project Profile。
2. 创建知识库目录和 `_index.md`。
3. 盘点用户提供的 PRD、README、架构、接口和历史测试材料。
4. 可选扫描已绑定仓库中的 README、OpenAPI、数据库模型和模块结构。
5. 生成知识候选和来源引用。
6. 将冲突、缺失或低可信信息写入 `_gaps.md`。
7. 用户可以选择“仅确认需求”或“确认需求并沉淀所列知识”；只有后一种选择才将候选
   升级为 `confirmed` 知识。

系统必须区分：

- `observed`：从输入材料中直接提取。
- `inferred`：根据多个来源推断。
- `confirmed`：用户或权威来源已确认。
- `deprecated`：已失效但为历史追溯保留。

### 7.4 知识更新策略

工作流发现新的稳定领域知识时，只生成 Knowledge Proposal。需求文档通过 Gate 不等于
知识写入授权；可以在一次交互中同时确认需求和明确列出的知识候选，但默认的“仅确认
需求”不会写知识库。一次性变更细节、临时环境信息和当前 Bug 证据不得写入长期知识库。
已有知识页不得在该快捷流程中静默覆盖。

## 8. Planner 与 Readiness Engine

### 8.1 输入

Planner 接收：

- 用户目标
- 当前 scope
- Project Profile
- 当前 Artifact Inventory
- Resource 可用性
- 用户权限和环境状态
- Workflow Pack 中的 Capability 定义

### 8.2 输出

Planner 输出可解释计划：

```yaml
goal: test_cases
scope_id: checkout
available_inputs:
  - prd
  - knowledge_base
missing_inputs:
  - requirement_spec
  - risk_analysis
  - test_points
steps:
  - capability: requirement-specification
    reason: test_cases 的前置依赖
  - capability: document-risk-analysis
    reason: test_cases 的前置依赖
  - capability: test-point-design
    reason: test_cases 的前置依赖
  - capability: test-case-design
side_effects: []
```

无 Artifact 产出的入口阶段也是计划的一部分。例如 Feature Quality 必须先显示并完成
`feature-intake`，再进入 Requirement Specification；Bug 与 Release 同样先完成各自的
Intake/Baseline Gate。

### 8.3 动作状态

每个 Capability 计算以下状态之一：

- `available`：硬依赖满足，可以执行。
- `recommended`：当前最合理的下一步。
- `blocked`：缺少硬依赖、权限、环境或确认。
- `completed`：当前版本产物已就绪。
- `stale`：产物存在，但上游已变化。
- `optional`：不影响目标达成的增强步骤。

### 8.4 自动补齐规则

如果目标缺少可以通过本地分析安全生成的前置产物，Planner 可以将其加入计划，但必须在执行前向用户展示完整步骤。

如果缺失项需要外部选择或会实质改变结果，例如存在两份互相冲突的需求基线，Planner 必须暂停并请求用户决定，不能自行选择权威版本。

### 8.5 本地产物生命周期

一次本地生成拆成可审计的三个动作：

1. `plan` 根据当前 Inventory 选择 Capability。
2. `run` 将 Capability 映射到既有 Workflow/Phase/Skill，并准备同一份 Run State。
3. `scaffold` 通过 `copy_template.py` 创建纯 Markdown，并在 `runs/<run-id>/artifacts/` 创建 draft Artifact record。
4. `gate` 调用类型 Validator 和严格 Stage Gate，同时检查上游 Artifact revision 和 ready 状态；只有通过后才能标记为 ready。

模板结构和内容规则由 Agent-next 已有类型 Validator 维护，Phase 完成条件由 Stage Gate 维护；Inventory 负责 revision/stale 和 ready 内容哈希漂移。未填写模板、残留占位符、缺失内容、缺失证据、未通过前序 Gate、缺失上游、revision 漂移或 ready 后内容变化都必须阻止 ready 或将产物标记为 stale。`scaffold` 不覆盖已有 Artifact ID，也不执行远端或共享环境操作。

## 9. Feature Quality 工作流

Feature Quality 是默认功能测试 Playbook，支持从不同输入成熟度开始。

### 9.1 能力契约

| 能力 | 硬依赖 | 软依赖 | 输出 | 主要门禁 |
|---|---|---|---|---|
| 项目初始化 | 项目名称 | 背景文档、仓库 | Profile、知识骨架 | 配置和知识索引有效 |
| PRD 补充需求 | PRD、知识库 | 代码、历史需求 | 需求规格 | 假设、冲突、验收标准已列出 |
| 需求 Review | PRD、需求规格、知识库 | 原型、接口文档 | Review、文档级风险 | 冲突和缺口已显式记录 |
| 代码风险走读 | 需求或风险项、产品仓库 | MR、commit、diff | 代码验证风险 | 每个结论有具体代码证据 |
| 测试点设计 | PRD、需求规格 | 风险分析、代码 | 测试点 | 需求和风险覆盖关系完整 |
| 测试用例设计 | 需求规格、风险分析、测试点 | 代码、历史用例 | 测试用例 | 可执行、可判定、可追溯 |
| 上传用例平台 | 测试用例 | 目录映射 | 同步记录、远端 ID | 预览、确认、结果回填 |
| 自动化归类 | 测试用例 | 自动化仓库 | 分类结果 | 分类理由和阻塞项完整 |
| 接口自动化 | API 类用例、接口信息、API 测试仓库 | OpenAPI、环境 | 自动化实现 | 本地验证或明确待验证项 |
| Web 自动化 | Web 类用例、页面信息、Web 测试仓库 | 原型、稳定选择器 | 自动化实现 | 本地验证或明确待验证项 |
| 测试执行 | 可执行用例、目标环境 | 数据工具 | 执行记录 | 环境确认、证据和失败分类 |
| 测试报告 | 需求、用例、执行记录 | Bug、风险、覆盖率 | 测试报告 | 结论与现有证据一致 |

### 9.2 需求规格

当只有 PRD 时，Agent-next 必须结合知识库生成可测试的需求规格，至少包含：

- 目标和非目标
- 用户角色与权限
- 主流程和异常流程
- 业务规则
- 数据和状态变化
- 接口或外部依赖
- 兼容性和迁移要求
- 验收标准
- 假设、冲突和未决问题
- 来源引用

一个 Feature / scope 生成一个需求规格 Artifact，但 Artifact 内应按可独立判定的
义务或用户可观察结果拆成多个 Atomic Requirement。不同触发条件、入口、状态、分支、
结果、来源或确认状态应拆分；测试数据与等价示例不作为独立需求。后续 Risk、Test Point
和 Test Case 必须引用 Atomic Requirement ID，不能只引用需求规格 Artifact 或上游
Feature ID 来声明整体覆盖。

每个 Atomic Requirement 必须记录精确来源、依据类型和确认状态。权威来源明确陈述与
用户明确确认可以形成已确认需求；测试设计推导不得写回为来源事实；代码、配置和运行
现象只能作为实现证据或差异，未经权威来源或用户确认不得升级为规范性产品要求；假设
必须保持待确认并关联开放问题。

知识不足不应阻止草稿生成，但产物状态只能是 `draft`，并必须显示缺失信息对测试设计的影响。

### 9.3 需求 Review 与文档级风险

当 PRD 和需求规格同时存在时，Review 应比较：

- 遗漏
- 冲突
- 歧义
- 不可测试描述
- 权限和数据边界
- 异常处理
- 兼容性
- 非功能约束

Review 可生成文档级风险，但不能声称风险已经过代码验证。

### 9.4 风险成熟度

风险分析使用同一份可持续更新的 Artifact，不拆成互不关联的“部分版”和“完整版”。

```yaml
assessment_level: document_assessed | code_verified
coverage_status: partial | complete
```

每个风险项至少记录：

```yaml
id: RISK-001
source: REQ-001
type: security
subtype: information_disclosure
tags: [enumeration, negative_path]
statement: 登录失败响应差异可能暴露账号存在性
status: pending_validation
level: P1
problem_essence: 不同账号状态返回可区分响应
trigger_conditions: [提交不存在账号或错误凭证]
impact: 攻击者可能枚举有效账号
doubts: [不同入口是否共用失败响应尚未确认]
validation_method: 比较不同账号状态的响应、提示和时延
evidence_level: document
verification_status: unverified
code_references: []
decision_note: none
```

`type` 是且仅是一个 Primary Risk Type；`subtype` 表示具体失效模式，`tags[]`
表示 timing、concurrency、permission、boundary、recovery 等横切特征。通用类型包括
`functional`、`security`、`integration`、`data`、`state`、`configuration`、
`compatibility`、`performance`、`availability_resilience`、`usability` 和
`observability`。Risk Type 只选择候选测试维度和技术，不能脱离触发条件、影响、疑点
和证据机械生成测试点或测试用例。

风险详情是单条风险内容的权威来源，风险矩阵只作摘要和导航。详情必须分别记录状态、
等级、问题本质、触发条件、影响、疑点和验证方式；提供代码库且结论依赖源码时必须记录
精确代码证据，未提供代码库时显式写 `not_available`。风险接受或驳回的决策依据写入
`decision_note`，不能混入状态值。

代码走读后逐项更新为 `verified`、`contradicted` 或继续保持 `unverified`，不得因为读取过仓库就整体标记为完整。

### 9.5 测试点设计

测试点设计的硬依赖是 PRD 与需求规格。风险分析和代码是增强输入：

- 有风险分析：测试点必须映射风险覆盖。
- 有代码：补充实现边界、依赖和回归影响。
- 无代码：允许完成，但标记 `code_verification: not_performed`。
- 无风险分析：Planner 应推荐先生成文档级风险；用户显式跳过时，测试点标记覆盖局限。

Test Point 是覆盖设计的权威 Artifact，Test Case 只负责把 Test Point 实例化为
测试数据、步骤和可观察结果。Requirement 定义规范事实，Risk 决定覆盖优先级；Test
Point 不替代二者，但所有用例覆盖必须回到 Test Point 或显式 Coverage Gap。

Stage Gate 必须在当前 Run 的 Artifact 上建立 `REQ/RISK/TP/TC/BR/Q` ID registry，
检查重复定义以及正文和 Run State 中的 dangling reference。Test Points Artifact 还要
在单文件 Gate 中验证 Requirement Coverage、Risk Coverage、辅助矩阵和追溯区域引用的
每个 `TP-###` 都在测试点列表中定义。任何 dangling reference 都是 ERROR，不得按
相近编号自动纠正。`RA-###` 在定义正式语义和声明位置之前不进入 registry，出现时按
unsupported reference 阻断。

### 9.6 测试用例设计

测试用例的硬依赖是需求规格、风险分析和测试点。缺少其中任何一项时，Planner 应先安排补齐，而不是静默生成弱用例。

用例必须：

- 一条用例只验证一个清晰目标。
- 不以用例数量作为质量目标；相同前置条件、操作路径、观察面、预期结果、断言依据、
  优先级和追溯关系的数据条件应合并为一个行为用例和多个 `DATA-###` 参数行，每行可
  独立执行和记录结果。
- 前置条件明确。
- 步骤可执行。
- 预期结果可观察、可判定。
- 每条预期结果记录 `requirement`、`business_rule`、`contract`、`risk_derived` 或
  `hypothesis` 类型及精确来源。测试人员推导出的安全或性能检查不得伪装成 PRD 断言；
  失败后按来源判定为候选实现缺陷、需求缺口、风险发现或改进建议，而不是自动全部建 Bug。
- 映射需求、风险和测试点。
- 明确自动化适配性。

平台或共享框架涉及认证、授权、会话、租户、路由、共享配置或公共客户端基础设施时，
Test Analysis 必须显式评估 Security、Availability / Resilience、Performance 和
Compatibility，并为每类记录已覆盖的 Risk / Test Point、Coverage Gap 或带理由的
`not_applicable`。这是一项覆盖评估，不是固定用例清单；浏览器矩阵、性能阈值、环境和
故障注入能力必须来自 Project Profile 或权威项目证据。

### 9.7 用例平台同步

禅道通过 Skill 接入。通用 Capability 为 `case-management-sync`，现有客户端
能力应通过参数化的 `zentao-sync` Skill 复用，不得重写禅道客户端。

同步流程：

1. 校验本地用例。
2. 生成新增、更新、跳过、冲突预览。
3. 显示目标项目、模块和预计写入数量。
4. 获取用户显式确认。
5. 执行写入。
6. 将远端 ID、失败项和重试信息回填到同步记录。

### 9.8 自动化归类

分类结果至少包括：

- `api`
- `web`
- `integration`
- `data_verification`
- `manual_only`
- `not_recommended`
- `blocked`

分类必须记录理由、依赖、预计稳定性和阻塞项。没有自动化仓库时仍可完成分类，但不能声称已经实现。

分类同时记录自动化等级 `A0/A1/M0/N0`。目标以核心验证对象为准：页面仅用于准备数据时，
接口响应或后端状态仍是 `api`；只有浏览器和接口两类断言都不可替代时才是 `hybrid`。
生成前必须先匹配现有覆盖，并记录依赖、副作用、目标仓库和决定依据。

### 9.9 自动化实现

API 与 Web 自动化分别由 Skill 实现；Skill 优先调用项目已有测试框架和工具。只有多个
Skill 确实需要共享稳定底层驱动时才增加薄 Adapter。它们共享以下契约：

- 输入标准测试用例。
- 读取 Project Profile 选择目标仓库和分支策略。
- 读取仓库自己的贡献规范和测试模式。
- 生成或更新最小范围代码。
- 在允许的本地环境中验证。
- 记录文件、命令、结果和未验证项。
- 不自动向保护分支提交或推送。

内置的 `pytest-yaml-api` 是 `api-automation` slot 的一个通用实现：它生成薄 pytest
项目与可追溯 YAML case，并复用独立版本化的 `rigorpath-api-test` 运行时。Core 不包含
产品端点、认证或租户逻辑；每个 `AUTO-###` 必须保留 `TP-###`、`TC-###` 及断言来源，
静态校验失败或存在悬空引用时不得进入执行阶段。性能/Locust 不属于该实现的默认 MVP。
当 Project Profile 声明唯一的 API automation repository 时，Skill 在该
`repositories.automation[].path` 生成业务测试项目，并通过 `uv sync` 从
`runtime_url@runtime_revision` 获取运行时。revision 必须是不可变 tag 或 commit；已有非空
目录只复用、不覆盖。

`agent-next init --automation api` 从声明式 automation preset 生成上述 repository 与
integration 配置，但初始化阶段不访问网络。完成并确认 `automation_classification` 后，
`agent-next prepare-automation` 仅对 `A0/A1 + api/hybrid` 行调用 Profile 选择的 Skill
provider；无符合条件的行明确 skip。Core 只读取 provider contract，不包含 pytest、端点、
认证或产品规则。

### 9.10 测试执行与报告

执行记录必须区分：

- passed
- failed
- blocked
- skipped
- not_run
- infrastructure_error

报告不得把 `blocked`、`skipped` 或 `not_run` 计为通过。报告结论必须从执行记录和现有证据计算，不能只使用生成文本中的主观判断。

`test-execution` Skill 负责确认后的 runner 执行与证据归一化。对自动化执行，它从 JUnit
XML 和 YAML case inventory 生成 `execution_record`，保留命令、退出码、revision、执行窗口
及证据路径；没有 runner 结果的计划用例是 `not_run`，runner/collection 崩溃是
`infrastructure_error`。Reporting 只消费规范化记录。

## 10. Bug Regression 工作流

Bug Regression 的资产链为：

```text
问题描述
  → 修复范围
  → 影响分析
  → 现有覆盖匹配
  → 回归决策
  → 回归计划/补充用例
  → 执行记录
  → 回归报告
```

### 10.1 最小输入

以下任一输入均可启动：

- Bug ID
- Issue 链接
- 明确的问题描述
- 修复 MR / PR
- 修复 commit / diff

### 10.2 核心规则

1. 先确认原始失败表现和预期行为。
2. 有修复代码时，必须记录实际变更文件、符号和依赖影响。
3. 优先匹配已有测试覆盖，再决定是否补充用例。
4. 回归范围必须同时覆盖原始失败、修复路径和合理的邻接影响。
5. 没有执行证据时只能输出回归计划，不能输出“回归通过”。
6. Bug 平台的更新、关闭、重新打开和指派均需要显式确认。

## 11. Release Acceptance 工作流

Release Acceptance 的资产链为：

```text
版本基线
  → 范围汇总
  → Scope Gap
  → 风险和执行优先级
  → 验收计划
  → 验收执行
  → 发布结论
  → 可选上线观察
```

### 11.1 范围来源

Release 范围应综合：

- Release Note
- 需求、任务和 Bug
- Tag 或分支 diff
- 配置、迁移和 Feature Flag
- 依赖和基础设施变更
- 已知问题和明确排除项

Tag diff 只能作为范围初始化信息，不能成为唯一权威来源。来源不一致时记录 `Scope Gap`。

### 11.2 资产复用

Release 不复制 Feature 或 Bug 的测试资产。验收计划通过 Artifact ID 和 revision 引用已有需求、风险、用例和自动化资产。

### 11.3 发布结论

建议标准结论：

- `go`
- `go_with_known_risks`
- `no_go`
- `insufficient_evidence`

结论必须列出阻塞项、未执行范围、已接受风险和证据引用。

## 12. 用户交互设计

### 12.1 首次使用

首次引导只询问用户能够直接回答的信息：

1. 项目名称和目标。
2. 当前有哪些文档。
3. 是否绑定代码仓库。
4. 当前最想完成什么。

集成平台、环境和自动化仓库在实际需要时渐进配置，不要求首次启动全部完成。

### 12.2 对话式入口

用户可以直接表达目标：

> 我只有一份 PRD，帮我完成测试用例设计。

系统应返回：

```text
已识别：
✓ PRD
✓ 项目知识库
✗ 需求规格
✗ 风险分析
✗ 测试点
✗ 测试用例

建议计划：
1. 根据知识库补充需求规格
2. Review 需求并生成文档级风险
3. 生成测试点
4. 生成测试用例

本计划只生成本地文件，不会修改远端系统。
```

### 12.3 CLI 入口

当前统一 CLI 提供：

```bash
agent-next init
agent-next doctor
agent-next env
agent-next inventory
agent-next register
agent-next plan --project <profile> --workflow <pack> --scope <scope> --goal test_cases
agent-next run --project <profile> --workflow <pack> --capability <id> --run-id <run>
agent-next scaffold
agent-next gate
agent-next record
agent-next knowledge
agent-next prepare-automation
agent-next status --run-id <run>
agent-next explain --run-id <run>
```

命令职责：

| 命令 | 职责 |
|---|---|
| `init` | 创建 Project Profile 和知识库骨架 |
| `doctor` | 检查 Profile、知识、Workflow、模板和已选择的 automation provider |
| `env` | 只显示环境变量是否配置，不显示值或声称连通性有效 |
| `inventory` | 盘点已有资产及其 revision、状态和缺口 |
| `register` | 将已有本地文件登记为 Artifact，不复制或改写正文 |
| `plan` | 只生成计划，不执行 |
| `run` | 将选定 Capability 写入既有 Run State，准备 Workflow/Phase/Skill 执行上下文 |
| `scaffold` | 从正式模板创建 draft Artifact 并登记 Run State |
| `gate` | 执行 Artifact Validator 与当前 Stage Gate，可显式标记 ready |
| `record` | 记录当前 Run 的知识、证据和说明 |
| `knowledge` | 预览或显式确认可复用知识提案 |
| `prepare-automation` | 对已归类的 API 用例准备 Profile 选择的 automation consumer |
| `status` | 展示当前 Run 和 Artifact 状态 |
| `explain` | 展示 Gate、证据、Skill receipt 和决策原因 |

### 12.4 项目主页信息架构

如果后续提供 Web/TUI，应优先展示资产，而不是内部 Phase：

| 资产 | 状态 | 证据等级 | 最近更新 | 下一步 |
|---|---|---|---|---|
| 知识库 | 有缺口 | 中 | 今天 | 补充 |
| PRD | 已就绪 | 高 | 今天 | 查看 |
| 需求规格 | 待生成 | — | — | 生成 |
| 风险分析 | 被阻塞 | — | — | 查看依赖 |
| 测试点 | 被阻塞 | — | — | 查看依赖 |
| 测试用例 | 被阻塞 | — | — | 查看依赖 |

每个阶段完成后只需要优先展示：

1. 生成或更新了什么。
2. 使用了哪些输入和证据。
3. 哪些结论未验证或存在缺口。
4. 推荐的下一步。

内部 workflow、phase、skill、receipt 和 gate 默认折叠，在 `explain` 中提供。

## 13. Run State

Run State 继续作为审计和恢复机制，但用户不直接维护。

建议 v0.1 状态：

```yaml
schema_version: 1
run_id: feature-checkout-20260901
project_id: shop-platform
goal: test_cases
workflow: feature-quality
current_capability: test-case-design
tracks: [web, backend]

plan: []
resources: []
knowledge_used: []
evidence: []
artifacts: []
traceability: []
confirmations: []
skill_receipts: []
gate_results: []
events: []
```

与旧模型相比：

- `project_id` 取代任何全局单项目假设。
- `tracks[]` 由各 Project Profile 自行定义，Core 不提供产品线字段。
- `goal` 和 `current_capability` 取代要求用户理解的固定 phase。
- Workflow 和 Capability 均由声明式配置解析。
- `events[]` 记录状态变化，用于恢复和解释。

## 14. Gate Engine

Gate 分为四类：

### 14.1 Input Gate

检查硬依赖 Artifact 是否存在、状态是否可用、revision 是否匹配。

### 14.2 Evidence Gate

检查结论是否具备对应等级的实际证据。例如 `code_verified` 风险必须包含代码引用。

### 14.3 Artifact Gate

根据 Artifact Schema、模板章节和类型专属 Validator 验证产物。

### 14.4 Action Gate

检查环境、权限、确认和副作用策略。

所有 Gate 均应返回结构化结果：

```yaml
status: failed
code: MISSING_CODE_EVIDENCE
message: 风险分析声明为 code_verified，但 RISK-003 没有代码引用。
remediation:
  - 补充代码证据
  - 将 assessment_level 降级为 document_assessed
```

## 15. Skill-first 集成设计

v0.1 复用 Agent-next 已有 Skill 体系。Workflow/Capability 声明所需 Skill，Skill
调用现有 CLI、SDK、仓库工具或测试框架。不得为了统一接口而重写已有平台客户端。

### 15.1 标准 Skill slot

- `document-source`
- `source-control`
- `repository-analysis`
- `requirement-tracker`
- `issue-tracker`
- `case-management-sync`
- `api-automation`
- `web-automation`
- `test-execution`
- `execution-environment`
- `reporting`

Project Profile 将 slot 映射到具体 Skill：

```yaml
integrations:
  api_automation:
    skill: pytest-yaml-api
    config:
      runtime_url: https://github.com/phoenine/rigorpath_api_test.git
      runtime_revision: <immutable-tag-or-full-commit>
  test_management:
    skill: zentao-sync
    config:
      module_mapping: config/zentao-modules.yaml
```

### 15.2 Adapter 的有限职责

Adapter 是可选的薄驱动，不是默认扩展方式。只有多个 Skill 确实需要共享一个稳定、
可独立测试的底层协议转换时才增加 Adapter。Skill 仍负责路由、preview、确认、证据
和结果解释。v0.1 不重新实现 `zentao-cli`、Git、pytest、Playwright 等已有能力。

### 15.3 安全要求

- 凭证只能从环境变量或外部 Secret Provider 读取。
- 配置、Run State、Artifact 和日志中不得保存明文凭证。
- 所有写操作必须支持 dry-run 或 preview。
- 写操作结果必须记录部分成功、失败项和远端 ID。
- 不允许用通用 shell、Skill 或 Adapter 绕过确认策略。

## 16. 输出与目录路由

`outputs/` 只保存用户可阅读的最终 Markdown；Artifact ID、revision、来源、证据和
Gate 状态统一保存在 `runs/<run-id>/artifacts/*.json`。输出按项目和工作 scope 路由：

```text
outputs/<project-id>/
├── features/<requirement-name>/
│   ├── requirement-spec.md
│   ├── risk-analysis.md
│   ├── test-points.md
│   ├── test-cases.md
│   ├── execution-record.md
│   └── run-summary.md
├── bugs/<bug-id-or-name>/
│   ├── change-scope.md
│   ├── regression-plan.md
│   └── regression-report.md
└── releases/<release-id>/
    ├── release-scope.md
    ├── acceptance-plan.md
    ├── execution-record.md
    └── acceptance-report.md
```

Release 资产仍应引用 Feature/Bug 资产，而不是复制它们。

## 17. 项目扩展边界

具体项目的 Track、知识、仓库映射、自动化规则、数据准备和验收策略不得随
通用仓库分发。它们应由使用方在下游 Project Profile、私有 Skill 包或本地环境中
提供。通用仓库只维护这些扩展所依赖的 Schema、Skill slot、确认门禁和无业务含义
的示例。

迁移原则：

1. 通用 Core 不读取旧项目 Run State 或项目专属输出目录作为 Core Inventory。
2. 需要保留的旧产物通过 `register` 显式登记到新的 Run Artifact Registry。
3. Core 测试不得依赖任何真实项目的数据、目录、凭证或私有 Skill。
4. 项目扩展的兼容验证在其下游包中完成。

## 18. v0.1 产品边界

### 18.1 已支持范围

- Project Profile Schema 和加载器
- 标准知识库模板和 `init`
- Artifact Schema、Inventory 和状态计算
- 声明式 Capability Schema
- Planner 与依赖解析
- 通用 Run State
- Input、Evidence、Artifact、Action Gate 基础框架
- Feature Quality 基础链路：PRD → 需求 → 风险 → 测试点 → 测试用例
- Bug Regression 基础链路
- Release Acceptance 基础链路
- 迁移并参数化 Agent-next 已有 Router、Run State、Stage Gate、模板和 Validator
- Project Profile 仓库路由与 Skill slot 映射；Adapter 只在现有能力无法复用时实现薄驱动
- 需求、风险、测试点、测试用例、自动化、执行、报告与禅道同步 Skills
- `doctor`、`inventory`、`plan`、`run`、`scaffold`、`gate`、`record`、
  `knowledge`、`prepare-automation`、`status`、`explain`
- 下游项目扩展接口和通用契约测试

### 18.2 非目标

- 完整 Web UI
- 多用户权限系统
- 云端任务队列
- 在线知识图谱服务
- 所有第三方平台的官方 Skill/Adapter 扩展
- 自动提交 PR/MR
- 生产环境自动执行
- 跨项目共享知识市场

## 19. v0.1 验收标准

v0.1 至少通过以下场景：

1. **空项目初始化**：只有项目名称，也能创建有效 Profile、知识库入口和 Gap 清单。
2. **仅 PRD**：能够规划并生成需求规格、文档级风险、测试点和测试用例。
3. **已有需求**：能够复用需求文档执行 Review，而不重复生成。
4. **代码风险验证**：能够把单个风险从 document evidence 升级为 code evidence，并引用具体文件或符号。
5. **缺少软依赖**：无代码时允许生成测试点，但明确显示未进行代码验证。
6. **缺少硬依赖**：只有需求文档而没有风险和测试点时，测试用例目标自动规划补齐步骤。
7. **上游变化**：需求 revision 变化后，相关风险、测试点和用例被标记为 stale。
8. **副作用拦截**：未确认时无法写入禅道或在共享环境执行。
9. **Bug 回归**：能够从 Bug 描述或修复 diff 形成影响分析、覆盖匹配、计划和报告。
10. **Release 验收**：能够汇总多个 Track，记录 Scope Gap，并引用已有测试资产。
11. **项目隔离**：两个 Project 的配置、知识、Run 和 Output 不互相污染。
12. **扩展隔离**：具体项目的 Profile、知识和 Skill 不进入通用仓库。

## 20. 测试策略

### 20.1 单元测试

- Profile Schema 校验
- Artifact 状态和 stale 传播
- Capability 依赖解析
- Planner 最短可行计划
- Gate 错误码和修复建议
- 输出路由和路径安全

### 20.2 契约测试

- 每种 Artifact 模板和 Validator
- 每种集成 Skill 的 read/preview/write 契约；存在薄 Adapter 时补充其驱动契约
- Workflow Pack 与 Capability Schema
- Run State 的序列化和迁移

### 20.3 场景测试

- 空知识库
- 仅 PRD
- PRD + 需求
- 需求 + 代码
- 完整测试设计链路
- Bug 回归
- Release 验收
- 上游变更导致下游 stale
- 远端写入确认

### 20.4 真实行为验证

自动化测试只能证明契约和受控环境行为。涉及浏览器选中状态、真实平台写入、共享环境执行和报告可访问性时，必须保留运行时验证步骤，不能只依据单元测试宣称完成。

## 21. 可观测性与错误体验

每次执行应产生结构化 Event：

```yaml
time: 2026-09-01T12:10:00+08:00
type: gate_failed
capability: test-case-design
code: MISSING_REQUIRED_ARTIFACT
details:
  artifact_type: risk_analysis
```

面向用户的错误信息必须说明：

1. 当前无法做什么。
2. 缺少什么或哪项验证失败。
3. 为什么它影响结果。
4. 系统可以自动处理什么。
5. 用户需要决定什么。

不得只返回内部异常、Schema 路径或 Python traceback。

## 22. 最终用户心智模型

Agent-next 对用户暴露的核心概念应限制为五个：

1. **Project**：我正在测试哪个项目。
2. **Inputs**：我当前有哪些文档、代码和环境。
3. **Goal**：我想得到需求、风险、用例、自动化、回归或验收结论中的哪一种结果。
4. **Plan**：系统准备如何补齐依赖并完成目标。
5. **Evidence**：结论由哪些材料、代码或执行结果支撑。

Workflow、Capability、Skill、Receipt、Gate 和 Run State 是系统可靠性的基础设施，默认不应成为用户开始使用 Agent-next 的前置知识。
