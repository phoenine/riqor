<p align="center">
  <img src="docs/images/2.png" alt="Rigor 标志" width="520">
</p>

# Riqor（Agent-next）

<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</p>

Agent-next 是一个与具体项目无关的测试工程 Agent 工作区。用户只需提供已有资料和期望结果，Agent-next 就会盘点输入、规划缺失依赖、维护可追溯关系，并在执行外部副作用前请求确认。

v0.1 的设计详见 [`docs/agent-next-generalization-v0.1.md`](docs/agent-next-generalization-v0.1.md)。完整且经过验证的端到端示例请参阅 [Shop Platform 快速入门](docs/quickstart-shop-platform.md)。本实现复用并参数化了已验证的 Agent-next Workflow、Skill、Run State、Stage Gate、模板和校验器链路，而不是维护另一套并行执行模型。

## 架构概览

Core 包含路径解析器、阶段路由器、Run State 写入器/Schema/迁移器、模板复制器、产物校验器、测试用例校验器、Stage Gate，以及以下与项目无关的能力：

- Project Profile
- 产物元数据
- 声明式 Capability
- 声明式 Workflow 清单与 Stage Gate 规则
- 经 Schema 校验的自动化 Provider
- 知识库初始化布局
- 产物盘点与过期状态传播
- 感知 scope 的依赖规划

仓库提供通用的 `requirement-analysis`、`test-analysis`、`test-case-design`、`automation`、`test-execution`、`reporting`、`release-acceptance` 和 `zentao-sync` Skills。Capability 会引用其权威的 Workflow、Phase 和 Skill。每个 `workflows/<id>/workflow.yaml` 负责定义阶段顺序、文档、输出 scope 目录以及分阶段的 Gate 规则。自动化 Skill 通过经过 Schema 校验的 `provider.yaml` 暴露能力；Doctor 与准备流程共用同一个加载器。

产品专属的自动化与数据规则应放在下游 Project Profile 或私有扩展包中，而不是本仓库。`inventory`、`run`、`status`、`explain`、`scaffold` 和 `gate` 使用同一条执行链。产物身份、修订版本和可追溯信息保存在 `runs/` 中；`outputs/` 只保存面向用户的交付物。本项目不开发并行的 Adapter SDK 或第二套执行状态模型。

## 已迁移的执行基础设施

统一 CLI 之后，兼容命令仍可直接运行：

```bash
python3 tools/run_state.py --help
python3 tools/copy_template.py --help
python3 tools/validate_run_state.py --help
python3 tools/stage_gate.py --help
```

创建新的 Run State 时，请使用 Project Profile 标识，而不是旧的 product line：

```bash
python3 tools/run_state.py \
  --run-id demo \
  --project-id shop-platform \
  --track storefront \
  --entry feature-quality \
  --phase Intake
```

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

只填写本地实际需要的配置值。CLI 会读取仓库根目录的 `.env`，但不会覆盖当前 shell 或 CI 已提供的环境变量。可用 `agent-next env --group ZENTAO` 检查变量名称和是否存在，而不暴露变量值；详见 [`docs/environment.md`](docs/environment.md)。

## 在 Codex 或 Hermes 中使用

Agent-next 将面向 Agent 的 Skills 与确定性的本地 CLI 组合在一起。完成上述安装后，通过跨 Agent 通用的项目目录暴露仓库内置 Skills：

```bash
mkdir -p .agents
ln -s ../skills .agents/skills
```

请在仓库根目录执行这些命令。软链接让 Skill 继续保留在源码位置，因此 `skills/` 中的更新会立即对 Agent 生效。如果 `.agents/skills` 已存在，请有意识地复用或替换它，不要重复执行链接命令。

### Codex

在仓库中启动 Codex，使用 `/skills` 确认 `agent-next` 可用，然后通过 `$agent-next` 显式调用；也可以直接描述匹配的测试工程任务，让 Codex 自动选择该 Skill：

```text
$agent-next 盘点现有输入，并为 checkout 的 test_cases 目标制定计划
```

Codex 还会读取仓库中的 `AGENTS.md`，其中定义了项目契约和必须执行的验证命令。

### Hermes Agent

Hermes 会发现 `.agents/skills` 下的项目级 Skills。首次使用时信任当前克隆仓库，然后启动新会话，通过斜杠命令调用路由 Skill：

```bash
hermes skills trust
hermes chat -q "/agent-next 盘点现有输入，并为 checkout 的 test_cases 目标制定计划"
```

路由 Skill 只会加载当前工作流所需的下游 Skills。随后，两种 Agent 宿主都可以通过 `agent-next` CLI 完成盘点、规划、Run State 管理、产物创建和 Stage Gate 校验。远程写入、共享环境执行和共享数据变更仍然必须经过显式确认。

关于宿主端的具体行为，请参阅官方 [Codex Skills 文档](https://developers.openai.com/codex/skills)和 [Hermes Agent Skills 文档](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md)。

## 验证示例项目

```bash
agent-next doctor --project examples/shop-platform/project.yaml
```

预期结果：

```text
OK project shop-platform
OK knowledge index examples/shop-platform/knowledge/_index.md
OK capabilities 18
OK artifact templates 16
```

## 初始化新项目

创建一个带有标准知识目录结构的空项目：

```bash
agent-next init \
  --project-id my-product \
  --name "My Product" \
  --track web \
  --track backend \
  --default-track backend
```

初始化时注册已有的背景文档：

```bash
agent-next init \
  --project-id my-product \
  --name "My Product" \
  --source docs/product-prd.md
```

源文件必须已经位于仓库根目录下。它们会被登记到 `knowledge/<project-id>/_sources.yaml`，但不会被视为已经确认的知识。`init` 拒绝覆盖已有的 Project Profile 或知识根目录。

如果项目需要生成 API 自动化代码，请在初始化时声明集成类型：

```bash
agent-next init \
  --project-id iot-ops \
  --name "IoT Ops" \
  --automation api
```

该命令会在 Project Profile 中写入支持 API 的仓库条目，以及不可变的 `rigorpath-api-test` 运行时修订版本；初始化过程中不会下载任何内容。自动化分类审核完成后，用以下命令准备精简的消费端项目：

```bash
agent-next prepare-automation \
  --project config/projects/iot-ops.yaml \
  --classification-artifact AUTO-CLASS-001 \
  --test-cases-artifact TC-SUITE-001 \
  --implementation-artifact AUTO-IMPL-001 \
  --run-id automation-login
```

两个输入产物必须已经登记并处于 ready 状态。只有目标为 `api` 或 `hybrid` 的 `A0`、`A1` 行会触发准备流程，而且所有符合条件的行都必须将所选仓库声明为目标位置。

所选 Skill Provider 会创建 `repositories/automation/iot-ops-api-test` 并解析固定版本的依赖。随后命令会在同一 Run State 中创建草稿状态的 `automation_implementation` 产物。离线创建脚手架时使用 `--no-install`。

项目知识对用户而言是可选的。`init` 会创建一个空的内部上下文骨架，因此新项目可以只从描述或 PRD 开始。当需求工作发现稳定、可复用的知识时，请基于 `templates/knowledge/knowledge-proposal.yaml.tmpl` 记录提议文件：

```bash
agent-next record \
  --run-id checkout-requirement \
  --knowledge-proposal runs/checkout-requirement/order-timeout.yaml

agent-next knowledge \
  --project examples/shop-platform/project.yaml \
  --run-id checkout-requirement \
  --source-artifact REQ-checkout-001
```

第二个命令只预览名称和目标路径。如果用户明确选择“确认需求并持久化知识”，再使用 `--confirm` 应用列出的提议；仅确认需求会让这些提议继续保持 proposed 状态。该快捷命令永远不会覆盖已有知识页面。

同一个 `record` 命令可以记录结构化的 Stage Gate 证据，无需直接使用兼容版 Run State 脚本：

```bash
agent-next record \
  --run-id checkout-risk \
  --repository kind=dev,name=shop,path=repositories/product/shop,commit=<sha> \
  --repository-evidence repo=shop,evidence_type=commit,reference=<sha>,supports=RISK-001 \
  --required-env api \
  --checked-env api \
  --target staging \
  --confirmation id=CONF-001,action=shared_environment_execution,status=confirmed \
  --trace from=REQ-001,to=RISK-001,relation=analyzed_by
```

## 盘点产物并规划目标

产物元数据位于 `runs/<run-id>/artifacts/*.json`；`outputs/` 只保存面向用户的 Markdown 交付物。每个产物都属于一个 `scope_id`，例如功能、缺陷或发布 scope。

```text
outputs/<project-id>/features/<requirement-name>/requirement-spec.md
outputs/<project-id>/features/<requirement-name>/risk-analysis.md
outputs/<project-id>/features/<requirement-name>/test-points.md
outputs/<project-id>/features/<requirement-name>/test-cases.md
outputs/<project-id>/bugs/<bug-id-or-name>/regression-report.md
outputs/<project-id>/releases/<version>/acceptance-report.md
```

面向用户的文件名刻意不包含 Artifact ID 和修订版本。

```bash
agent-next inventory \
  --project examples/shop-platform/project.yaml \
  --scope checkout

agent-next plan \
  --project examples/shop-platform/project.yaml \
  --workflow feature-quality \
  --scope checkout \
  --goal test_cases
```

示例初始只有一个 ready 状态的 PRD。因此，计划会说明 Intake Gate，以及到达 `test_cases` 目标所需的四个产物生成步骤。安装多个 Workflow Pack 时，必须使用 `--workflow <pack-id>` 选择一个；Agent-next 不会代替用户猜测。`plan` 始终是只读操作。

## 准备运行、创建产物并校验阶段

从计划中的 Intake Gate 开始。该命令会记录权威的 Workflow、Phase、所需 Skills 和哈希凭据，但不会执行远程操作：

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
  --knowledge-plan-summary "The current project knowledge is sufficient" \
  --knowledge-used path=skills/requirement-analysis/references/intake-sources.md,purpose=intake \
  --note intake_input:PRD-checkout-001

agent-next gate \
  --project examples/shop-platform/project.yaml \
  --run-id checkout-requirement
```

Intake 通过后，将同一个 Run State 推进到第一个产物生成步骤，并根据其声明的模板创建脚手架：

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
  --run-id checkout-requirement \
  --source-artifact PRD-checkout-001@1 \
  --track backend
```

填写生成的 Markdown，更新 Workflow 阶段要求的 Run State 证据，然后执行校验：

```bash
agent-next gate \
  --project examples/shop-platform/project.yaml \
  --artifact-id REQ-checkout-001 \
  --run-id checkout-requirement \
  --mark-ready
```

`scaffold` 会委托继承的托管模板复制器，并在同一个 Run State 中登记产物。`gate` 会委托产物类型校验器和严格的 Stage Gate。如果模板未填写或仍含占位符、上游修订版本发生变化、源产物未 ready、前置阶段未通过，或者缺少要求的知识/仓库/确认凭据，它都会拒绝将产物标记为 ready。成功进入 ready 状态时会记录交付物的 SHA-256；之后内容发生变化时，Inventory 会将其标记为 stale。

查看实时状态和每个阻塞原因：

```bash
agent-next status --run-id checkout-requirement
agent-next explain --run-id checkout-requirement
```

## 运行测试

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## 仓库结构

```text
config/               Project Profile 注册信息
knowledge/            按项目隔离的可复用知识
workflows/            声明式工作流能力
skills/               面向 Agent 的工作流指令
templates/            知识与产物的托管 .md.tmpl 源文件
schemas/              公开的 JSON Schema 契约
tools/                Core 引擎、校验器、状态工具和 CLI
repositories/         本地产品、自动化和工具仓库镜像
outputs/              按项目隔离的生成交付物
runs/                 持久化执行状态
examples/             可运行的示例项目
docs/                 产品与架构文档
tests/                单元测试和契约测试
```

仓库本身就是运行时边界。Core 代码有意放在 `tools/` 中，不存在独立的 `src/agent_next/` 包目录。可编辑安装只为当前 checkout 提供 `agent-next` 命令。
