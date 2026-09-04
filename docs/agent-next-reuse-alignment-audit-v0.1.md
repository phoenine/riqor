# Agent-next → Agent-new 复用与通用化对齐审计 v0.1

> 日期：2026-09-02  
> 状态：R1、R2、R3 已完成；项目专属兼容包不随通用仓库分发
> 对齐基线：现有 `agent-next` 实现 + `agent-next-generalization-v0.1.md`

## 1. 审计目的

本审计纠正 Agent-new 前三个里程碑中过度采用 greenfield 实现的偏差。Agent-new
的目标不是依据设计文档重新实现一套 Agent-next，而是：

> 以已经运行和验证过的 Agent-next 为母版，保留其 Workflow、Skill、Run State、
> Gate、模板和工具链，通过 Project Profile、Track、声明式 Planner 和项目隔离完成
> 通用化。

后续开发必须同时满足两项约束：

1. 不丢失 Agent-next 已经证明有效的执行能力和安全门禁。
2. 不把具体产品、Track、仓库和私有知识固化进通用 Core。

## 2. 审计范围与证据

本次对比了以下内容：

- Agent-next：`AGENTS.md`、`skills/`、`workflows/`、`tools/`、`templates/`、
  `schemas/run-state.schema.json`、`config/projects.yaml`、`tests/`。
- Agent-new：当前 `tools/`、`schemas/`、`templates/`、`workflows/`、`tests/`、
  Project Profile 与示例项目。
- 产品设计：`docs/agent-next-generalization-v0.1.md`。

验证结果：

- Agent-next 使用具备 `PyYAML` 和 `jsonschema` 的 Python 环境运行 121 项测试，全部通过。
- `tools/check_repo.py` 的 project routing、knowledge、unit tests 和 diff whitespace
  四组检查全部通过。
- Agent-new 当前 41 项测试全部通过，但这些测试主要证明新建的最小 Core 自洽，
  不能证明它与 Agent-next 的真实 Workflow、Skill 和 Stage Gate 等价。
- 本次审计没有调用真实禅道或共享测试环境；ZenTao 结论来自现有 Skill、同步规则、
  Workflow 门禁和 CLI 调用约定，迁移后仍需做一次受控的真实行为验证。

## 3. 总体结论

### 3.1 必须停止的方向

1. 停止为禅道、API 自动化、Web 自动化重新开发一套平台 SDK 或 Adapter 框架。
2. 停止用 Agent-new 的简化模板替代 Agent-next 的成熟模板。
3. 停止用 `tools/artifacts.py::gate_artifact` 替代 Agent-next 的 Stage Gate。
4. 停止把简化 Capability YAML 当成完整 Workflow 的替代品。
5. 在复用迁移完成前，暂停继续增加新的 M4 功能。

### 3.2 应当保留的 Agent-new 新增价值

- Project Profile Schema 与项目隔离。
- 自定义 `tracks[]`，Core 不提供固定产品线枚举。
- 标准知识库初始化与 Knowledge Gap。
- Artifact Inventory、revision 与 stale 传播。
- 声明式 Capability 依赖和目标 Planner。
- `doctor`、`inventory`、`plan` 等面向用户的统一 CLI 门面。
- 项目级输出根和安全的 repo-relative path 契约。

这些能力应接入 Agent-next 的执行链路，而不是继续扩展成平行执行引擎。

## 4. 能力复用矩阵

| 能力 | Agent-next 已有实现 | Agent-new 当前实现 | 对齐决定 |
|---|---|---|---|
| Workflow 路由 | `skills/agent-next`、`workflows/index.md`、`phase_doc.py` | 简化 Capability Planner | 保留 Planner 作为目标规划层；执行路由复用 Agent-next |
| Feature Workflow | 8 个阶段、按需加载 Phase 和 Skill | 4 个 Capability | 迁移原 Workflow；Capability 仅作为可机器读取的索引 |
| Bug Regression | 8 个阶段，含 Intake、Decision Gate、执行和报告 | 6 个线性 Capability | 迁移原 Workflow；保留无 Artifact 的 Intake/Decision 语义 |
| Release Acceptance | 6 个阶段、Scope Gap、资产引用与结论门禁 | 4 个 Capability | 迁移原 Workflow 和 bundle 路由；Planner 只负责目标依赖 |
| Run State | Schema v2、创建、校验、迁移和恢复工具 | 尚未实现 | 复用并以 Project/Track 作为唯一项目身份模型 |
| Stage Gate | 849 行机器规则，检查 Skill receipt、知识、仓库、环境、确认、Artifact 和追溯 | 仅检查章节和上游 revision | 复用原 Stage Gate；当前 Gate 降级为 Artifact 内容 validator/facade |
| 模板创建 | `copy_template.py`，强制 frontmatter 并登记 Run State | 自行渲染 `.tmpl` 和 sidecar manifest | 复用 `copy_template.py`，扩展项目字段，不维护第二套弱模板 |
| Artifact 校验 | `validate_artifact.py`、`validate_test_cases.py`、类型专属规则 | section marker 完整性 | 原 Validator 为权威；新 Schema 可作为补充契约 |
| 需求分析 | 旧项目 Skill + references | 无执行 Skill | 提取通用 `requirement-analysis`，项目来源不进入 Core |
| 风险/测试点 | 旧项目 Skill + 方法论和源码证据规则 | 只有模板和 Capability | 参数化迁移为 `test-analysis`，不重新编写方法论 |
| 测试用例 | 旧项目 Skill + 三份强制 references + validator | 简化模板 | 复用 references、模板和 validator，命名通用化 |
| 自动化分类 | 旧项目 Skill、解析/分类/转换计划工具 | 尚未实现 | 参数化迁移为 `automation`；不新造分类引擎 |
| API/Web 自动化 | 项目测试框架 Skill | 空 Adapter 目录 | 留在下游私有扩展；通用层定义 Skill slot |
| 禅道 | 旧同步 Skill + `zentao-cli` + confirmation gate | 尚未实现，曾计划 Adapter | 提取为 `zentao-sync` Skill；不重写禅道 API 客户端 |
| 报告 | 旧项目 Skill + run-summary/regression/acceptance 模板 | 部分简化模板 | 参数化迁移为 `reporting` |
| 仓库路由 | `config/projects.yaml`、`paths.py`、`validate_projects.py` | Project Profile repository list | Project Profile 成为通用入口；复用路径和校验工具并兼容旧配置 |
| Knowledge | 成熟知识 Schema、validator、索引同步和使用记录 | 通用知识模板/Schema | 合并：保留通用分类，迁移 validator/索引/knowledge_used 机制 |

## 5. 当前重复实现与风险

### P0：新 Gate 不能替代现有 Stage Gate

`tools/artifacts.py::gate_artifact` 只检查模板章节、内容存在和上游 revision。
它没有检查：

- Router Skill 与下游 Skill 是否真正加载。
- Skill receipt 的路径和 sha256。
- 使用过的知识与代码证据。
- 仓库 revision、环境检查和用户确认。
- 前置 Phase、跨 Artifact traceability 和输出路由。
- 测试用例方法论/覆盖规则/写作规则 receipt。

因此该 Gate 只能保留为本地 Artifact 内容检查，不能再被称为完整 Stage Gate。

### P0：Agent-new 当前没有 Skill 执行层

`skills/` 为空，Capability 只能规划和创建空白 Markdown，无法复用 Agent-next
已经积累的需求、风险、测试点、用例、自动化和报告方法论。当前 M3 的“完整本地
生命周期”只完成了 scaffold/gate 的机械闭环，没有完成真实产物生成闭环。

### P0：简化模板造成能力退化

Agent-next 模板包含 YAML frontmatter、来源证据、知识使用、详细业务结构和类型专属
约束。Agent-new `.tmpl` 只保留少量 section marker。例如测试用例模板丢失了：

- `TC-00N` 标题约束。
- 优先级、禅道 ID、用例类型和可追溯关系。
- 前置条件、测试数据、步骤与预期结果的一一对应。
- 覆盖摘要和覆盖缺口。

不能以新模板替换旧模板。应从旧模板做项目无关的参数化，而不是重新设计弱模板。

### P1：Capability YAML 不是完整 Workflow

Agent-new 的 Workflow Pack 丢失了原有 Phase 文档、Required Skills、环境要求、
deliverable routing、optional skip、Decision Gate 和 machine gate rules。正确关系应是：

```text
Goal Planner
  → Workflow/Phase 路由
  → 当前 Phase 所需 Skill
  → copy_template / Validator / Stage Gate
```

Capability YAML 可以作为 Planner 的机器索引，但不能成为第二份 Workflow 真相源。
它必须引用现有 workflow、phase、skill 和 artifact type，并通过一致性测试防止漂移。

### P1：Artifact 类型已经发生漂移

通用化设计和 Agent-next 都包含 `automation_classification` 与 `run_summary`。Agent-new
当前模板注册表缺少这两类，却新增了 `release_baseline` 和 `release_scope`。原
Agent-next 将 Release Baseline/Scope 主要记录在 Run State 和 release bundle 中。
这些差异必须在迁移时明确，不得由新代码静默改写语义。

### P1：设计文档的 Adapter 表述会诱发重复开发

设计文档同时使用了 “Adapters / Skills” 和具体 Adapter 接口，但 Agent-next 的真实
集成方式是：Workflow 选择 Skill，Skill 调用已有 CLI、仓库工具或项目测试框架，
Stage Gate 负责确认与证据。禅道已经通过同步 Skill + `zentao-cli` 工作，
没有必要再次实现 `CaseManagementAdapter`。

审计已经将设计文档纠正为 Skill-first，但当前
`schemas/project-profile.schema.json` 的 integration 仍强制要求 `adapter`。迁移实施时
应改为优先接受 `skill`，仅在存在薄驱动时允许可选 `adapter`，并增加契约测试。

### P2：入口命名收敛

原 Agent-next 使用 `feature-testing`，但开源后的 Agent-new 不承担旧 Run State 的
兼容责任。唯一的功能工作流名称为 `feature-quality`：目录、Capability、Run State、
阶段路由和 CLI 均使用该名称，不提供 alias。

## 6. 纠偏后的目标架构

```text
用户目标
  → Agent-new CLI（init / doctor / inventory / plan / run / status / explain）
  → Project Profile + Artifact Inventory + Goal Planner      [Agent-new 新能力]
  → agent-next Router + Workflow + Current Phase             [复用]
  → 通用 Skill / Project Profile Skill                       [从现有 Skill 参数化]
  → copy_template + Validator + Run State + Stage Gate       [复用]
  → 现有 CLI / Repository / Automation Framework             [直接调用]
```

### 6.1 Skill-first 集成原则

- 外部平台和自动化首先通过 Skill 接入。
- Skill 负责读取平台规则、调用已有 CLI/SDK、展示 preview、请求确认并记录结果。
- 只有当多个 Skill 确实需要共享一个稳定、可测试的底层驱动时，才增加薄 Adapter。
- Adapter 不得重新实现已经由 `zentao-cli`、Git CLI、pytest、Playwright 等提供的能力。
- Profile 负责选择 Skill、配置资源和策略，不把平台名写入 Core 枚举。

示例：

```yaml
integrations:
  test_management:
    skill: zentao-sync
    config:
      module_mapping: config/zentao-modules.yaml
```

### 6.2 Profile 与 Skill 分工

| 内容 | 归属 |
|---|---|
| 项目 ID、Track、仓库、环境、输出路由 | Project Profile |
| 流程阶段和门禁 | Workflow Pack + Stage Gate |
| 需求/风险/测试设计方法 | 通用 Skills |
| 禅道同步规则 | `zentao-sync` Skill |
| 具体项目的 Track、仓库和自动化分支 | 下游 Project Profile |
| 项目测试框架的具体实现方式 | 下游私有 Skills |
| 凭证 | 环境变量或 Secret Provider，永不进入 Profile/Run State |

## 7. Agent-new 当前文件处置决定

### 7.1 保留并接入旧执行链

- `schemas/project-profile.schema.json`
- `schemas/artifact.schema.json`
- `schemas/capability.schema.json`
- `schemas/knowledge-*.schema.json`
- `tools/bootstrap.py`
- `tools/contracts.py`
- `tools/inventory.py`
- `tools/planner.py`
- `tools/doctor.py`
- `tools/cli.py` 和 `tools/agent_next.py`
- 对应 Profile、Inventory、Planner 和 path safety 测试

### 7.2 替换或降级职责

- `tools/artifacts.py`
  - `scaffold_artifact` 改为 `copy_template.py` 的 CLI facade。
  - `gate_artifact` 改为调用类型 Validator 和 `stage_gate.py`，不再单独定义完成条件。
- `templates/artifacts/*.md.tmpl`
  - 保留为用户交付物的成熟正文模板；Artifact 身份和追溯元数据进入 Run Artifact
    Registry，不在 Markdown 中维护第二份状态。
- `workflows/*/capabilities/*.yaml`
  - 只作为 Planner 索引，必须引用迁移后的 Workflow/Phase/Skill。
- `tests/test_artifacts.py`、`tests/test_workflow_packs.py`
  - 保留 Planner/CLI 场景；同时迁移 Agent-next 的模板、Gate、Run State 和 Skill receipt 测试。

### 7.3 从 Agent-next 迁移

优先直接迁移或做最小路径适配：

- `tools/paths.py`
- `tools/phases.py`、`tools/phase_doc.py`
- `tools/run_state_schema.py`、`tools/run_state.py`
- `tools/validate_run_state.py`、`tools/migrate_run_state.py`
- `tools/copy_template.py`
- `tools/artifact_frontmatter.py`
- `tools/validate_artifact.py`、`tools/validate_test_cases.py`
- `tools/stage_gate.py`
- `tools/parse_markdown_cases.py`、`tools/classify_specs.py`、
  `tools/generate_automation_plan.py`
- 三套 Workflow README、Phase 文档和全局 Stage Gates。
- 对应测试，迁移前以当前 121 项通过为基线。

### 7.4 参数化迁移，不直接进入 Core

- 旧产品线字段 → Project Profile `tracks[]`；Core 不解释旧值。
- 项目专属输出目录 → Project Profile 输出路由，Core 不保留旧目录默认值。
- `repositories/dev|test|tools` → Profile repository groups；保留旧 kind alias。
- 项目专属 Skills → 提取通用 Skill，项目特有内容留在下游扩展。
- 具体测试框架、数据注入和真实仓库分支 → 下游私有扩展。
- `config/projects.yaml` 中真实项目 ID、路径和描述 → 不进入默认开源 Profile。
- 项目知识、历史 `runs/`、`outputs/`、`.env`、仓库镜像 → 不复制到公开 Core。

## 8. 迁移执行顺序

### R0：冻结平行开发

- 不新增 Adapter SDK。
- 不扩展当前简化 Gate 和模板。
- 将本文加入开发约束。

### R1：迁移可验证基础设施

1. 迁移 paths、phase router、Run State、template copy、validator 和 Stage Gate。
2. 迁移对应测试，保证 Agent-next 121 项基线在新目录继续通过。
3. 将 Project/Track 作为统一项目身份字段接入。

完成记录（2026-09-02）：

- 已迁移 paths、phase router、Run State、schema/migrator、template copier、
  artifact/test-case validators 与 Stage Gate。
- 已合并 Agent-new 原有 41 项测试与本阶段迁移测试，共 136 项通过。
- 新运行态使用 `project_id + tracks`；Core 不保留项目专属身份或输出路由回退。
- 为保证迁移测试和 Skill receipt 可验证，三套 Workflow 与旧项目 Skills 曾作为
  兼容基线复制；它们属于 R2 的参数化对象，不能视为通用 Skill 已完成。

### R2：迁移 Workflow 和通用 Skills

1. 迁移三套 Workflow README、Phase 文档和 Stage Gate rules。
2. 从旧项目 Skills 提取通用 Skill，保留原 references 和方法论。
3. Capability YAML 引用 Workflow/Phase/Skill，不复制其规则文本。
4. 迁移 `zentao-sync` Skill，去除项目默认值，继续调用 `zentao-cli`。

完成记录（2026-09-02）：

- Stage Gate 与三套 Workflow 已切换到通用 Skill 名；通用执行链不再依赖
  项目专属 Skill。
- 已抽取 `requirement-analysis`、`test-analysis`、`test-case-design`、
  `automation`、`reporting`、`release-acceptance` 与 `zentao-sync`，保留原有
  方法论 references 和确认边界。
- `zentao-sync` 继续调用 `zentao-cli`；未新增禅道客户端或 Adapter SDK。
- Capability Schema 要求每项显式引用 `workflow + phase + skill`，Planner 加载时
  校验 Phase 和 Skill 确实存在。
- Project Profile integration 改为 Skill-first，`adapter` 仅作为可选薄驱动。
- 旧 Skill 名、Track 映射、专用自动化和数据注入规则不随通用仓库分发，
  需要时由下游扩展维护。
- R2 合并后共 145 项测试通过，8 个通用 Skill 均通过 `quick_validate.py`，
  通用 Intake Run State 与严格 Stage Gate 冒烟通过。

### R3：接回 Agent-new 新能力

1. `init` 生成 Project Profile 和知识库。
2. `inventory` 将 Run Artifact Registry 纳入 revision/stale 计算。
3. `plan` 把目标解析到已有 Workflow/Phase/Skill。
4. `run/status/explain` 复用 Run State 与 Stage Gate，不再自建状态模型。

完成记录（2026-09-02）：

- `inventory` 从 `runs/<run-id>/artifacts/*.json` 读取 Artifact revision/stale
  元数据；用户交付物保持纯 Markdown。
- `plan` 保持只读，并输出 Capability 对应的既有 Workflow、Phase 和 Skill。
- `run` 只准备既有 Run State：写入 Project/Track、Workflow/Phase、当前 Phase
  所需 Skill 与 SHA-256 receipt，不创建第二套执行状态。
- `status` 直接展示严格 Stage Gate 的当前结果；`explain` 展示 Phase 文档、
  Skill receipts、产物和同一组 blocker。
- `scaffold_artifact` 已成为 `copy_template.py` 的 facade；新增 Release Scope
  正式模板，注册表直接引用成熟正文模板与类型 Validator。
- `gate_artifact` 已改为类型 Validator + 严格 Stage Gate；Artifact Inventory
  只补充 revision/stale 判定，不再自定义一套完成规则。
- R3 收口后共 155 项测试通过。

加固记录（2026-09-03）：

- Artifact 元数据统一进入 `runs/<run-id>/artifacts/*.json`，用户交付物保持纯
  Markdown；旧产物通过 `register` 显式登记，不再由 Core 隐式扫描 frontmatter。
- 未填写的原始模板和显式占位符不能通过 Artifact Gate。
- ready Artifact 记录内容 SHA-256；文件缺失、历史托管记录缺少哈希或内容变化时，
  Inventory 将其标记为 stale。
- Planner 显式包含 Feature、Bug、Release 的无产物入口阶段，保证 predecessor Gate
  可以按公开 CLI 顺序完成。
- Inventory 按 `project_id` 隔离 Run Artifact Registry；其他 Project 的记录不再污染
  当前项目。
- 当前受控测试共 166 项通过；真实项目的私有迁移对照不包含在该数字中。

### R4：下游扩展边界

具体项目的兼容 Profile、私有知识、仓库 checkout、环境配置、数据准备规则和
迁移对照不进入通用仓库。通用测试只验证 Project Profile Schema、Skill slot、
Skill receipt、证据链与确认门禁；真实项目验证由下游扩展自行维护。

## 9. 合并验收门槛

复用迁移不能以“文件复制完成”为完成条件，至少满足：

1. Agent-next 当前 121 项测试迁入后继续通过。
2. Agent-new Profile/Inventory/Planner 的现有有效测试继续通过。
3. 三套 Workflow 的 phase 路由与 predecessor gate 通过。
4. Test Case 必须继续通过三份强制 reference receipt 和专用 validator。
5. 未确认的 ZenTao 写入、共享环境执行和共享数据修改被 Stage Gate 阻断。
6. 现有 `zentao-cli` Skill 调用路径可用，不存在第二套 ZenTao 客户端。
7. 下游 Profile 能表达自定义 Track 和输出路由，通用 Core 测试不依赖具体项目。
8. `agent-next-generalization-v0.1.md`、Workflow、Capability 与代码之间有一致性测试。

## 10. 后续开发决策规则

新增任何 Tool、Skill、Workflow、Template 或 Adapter 前，必须回答：

1. Agent-next 是否已经存在同职责实现？
2. 是否可以通过路径、Profile、Track 或配置参数化复用？
3. 是否已经读取相关 Workflow、Skill 和 tests？
4. 新实现是否会绕过现有 Run State、Stage Gate、Skill receipt 或确认边界？
5. 若必须替换，是否有迁移前后等价测试证明没有能力退化？

任一问题没有明确答案时，不进入实现。
