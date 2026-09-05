# Riqor 开源：把测试 Agent 从「会写」带到「可交付」

今年 6 月，我写过一篇《agent-next：把测试 Agent 接进流水线——工作流、门禁与 Lazy Load 的 Harness 实践》。当时它还是一套从具体项目里长出来的内部工具：能跑，但目录、知识和 Skill 都带着原项目的痕迹。文章最后留了一句话——换领域不换骨架，换模型不必重搭流程。

过去几个月，我们一直在补这句话后面的工程工作。现在，这套工具有了正式名字：**Riqor**，并已在 GitHub 开源。

项目地址：[github.com/phoenine/Riqor](https://github.com/phoenine/Riqor)

---

## 1. 为什么还要做一套测试 Agent 工作台

测试 Agent 最容易演示的，是输入一份 PRD，几分钟后生成需求分析、测试点和测试用例。真正接进团队流程后，问题通常出在另外几处：

- 已有用例能不能复用，还是应该重新生成？
- 需求变了以后，哪些下游产物已经过期？
- 这条风险结论来自 PRD、代码 Diff，还是模型自己的常识？
- 用例格式不合格时，流程能否真的停下来？
- 执行测试、修改共享数据、写入禅道之前，谁来确认？

这些问题靠一段更长的 Prompt 解决不了。它们需要稳定的资产模型、运行状态、证据链和机器门禁。

Riqor 做的，就是把这部分变成一套可以放进 Git、可以测试、也可以替换项目配置的 Harness。Agent 负责理解和分析；CLI 负责记账、检查依赖和裁决能不能进入下一阶段。

---

## 2. 这次开源的，不是原项目的脱敏副本

从 agent-next 到 Riqor，工作量最大的一部分不是删除项目名称，而是把项目差异从 Core 里真正拿出去。

现在，项目、Track、仓库、知识目录和环境策略都由 **Project Profile** 描述；Feature、Bug、Release 的阶段顺序和 Gate 规则放在声明式 **Workflow Pack** 中；需求分析、风险分析、用例设计、自动化、执行和报告由独立 **Skill** 承担。具体产品的字段、接口和数据规则不再是 Core 的枚举或默认值。

这意味着新项目不必复制一份引擎再修改。可以先用一条命令初始化：

```bash
agent-next init \
  --project-id my-product \
  --name "My Product" \
  --track web \
  --track backend \
  --default-track backend
```

如果手上已经有 PRD、Bug、发布基线或既有测试用例，也不用强制从第一阶段重来。Riqor 会先盘点现有资产，再围绕目标补齐缺失依赖：

```bash
agent-next inventory --project config/projects/my-product.yaml

agent-next plan \
  --project config/projects/my-product.yaml \
  --workflow feature-quality \
  --scope checkout \
  --goal test_cases
```

用户说的是「我要 checkout 的测试用例」，内部才需要回答应该复用什么、补什么、先过哪一道 Gate。阶段是系统的责任，不应该先变成用户的学习成本。

---

## 3. `outputs/` 给人看，`runs/` 给系统记账

早期实践里有一个很难绕开的矛盾：交付物既要方便人直接评审，又要保存 Artifact ID、修订版本、来源和 Gate 结果。把这些内容全塞进 Markdown，文件会越来越像数据库；全部藏起来，又失去追溯能力。

Riqor 把两者拆开：

```text
outputs/<project-id>/features/<scope>/test-cases.md
runs/<run-id>/artifacts/<artifact-id>.json
```

`outputs/` 只放需求说明、风险分析、测试点、测试用例和报告等可读产物；`runs/` 保存身份、版本、内容哈希、来源关系、证据和 Gate 状态。

上游需求从 `REQ-001@1` 更新到 `REQ-001@2` 后，下游用例不会继续假装自己是最新的；内容在 Gate 通过后又被修改，也会因为哈希变化被标记出来。这里没有依赖 Agent「记得回头检查」，而是由同一套状态与校验链处理。

---

## 4. 门禁不是提醒，而是确实会拦住

Riqor 保留了最初那条原则：规则要尽量进入工具和 Gate，而不是只写在文档里。

一个测试产物要变成 `ready`，需要同时满足模板、内容、前置产物、证据和当前阶段规则。模板里还有占位符、测试步骤与预期数量不一致、缺少代码证据、上游已经过期，都会得到明确的 blocker。

```bash
agent-next status --run-id checkout-test-design
agent-next explain --run-id checkout-test-design
agent-next gate \
  --project config/projects/my-product.yaml \
  --run-id checkout-test-design \
  --mark-ready
```

远程写入、共享环境执行、共享数据修改和部署则保留显式确认边界。Riqor 可以把执行计划准备好，但不会把「用户让我分析一下」解释成「可以顺便改远端数据」。

---

## 5. 一个可以自己跑完的例子

仓库里带了一个 `shop-platform` 示例，用 checkout 功能串起 PRD、需求说明、风险、测试点和测试用例，也提供 Release 验收材料。克隆后可以先做两件事：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

agent-next doctor --project examples/shop-platform/project.yaml
agent-next inventory --project examples/shop-platform/project.yaml
```

当前版本的示例检查结果为 18 个 Capability、16 个 Artifact Template；仓库全量单元测试共运行 228 项，全部通过。完整操作可以直接看 [Shop Platform 快速入门](quickstart-shop-platform.md)，通用化的边界和取舍则记录在 [v0.1 设计文档](agent-next-generalization-v0.1.md)。

Riqor 目前仍是 `0.1.0.dev0`。它已经具备可运行的工作流、产物注册表、Stage Gate、模板与校验器，以及面向 Codex、Hermes Agent 的 Skill 入口；但它不是一个点击按钮就能替团队完成所有测试的一体化平台。真实项目仍然需要自己的 Profile、知识和集成配置，自动化执行也仍然受环境与授权约束。

这个边界有必要说清楚。开源的价值不是把 Demo 包装成成品，而是让这套做法可以被检查、修改和继续验证。

---

## 6. 写在最后

我现在仍然认为，测试 Agent 的难点不是「能不能写出一份测试用例」，而是这份用例从哪里来、经过了什么检查、需求变化后是否还有效，以及下一步操作会不会越界。

之前那篇文章总结过一句话：

> Router 指路，Workflow 定阶段，Skill 承载专长，Knowledge 解释领域，Tool 执行门禁。

Riqor 的开源版本保留了这套骨架，又把具体项目从骨架里剥离了出去。你可以只从一份 PRD 开始，也可以带着已有用例和代码变更接入；可以使用仓库自带的三条 Workflow，也可以按照 Schema 增加自己的流程。

如果你也在尝试把测试 Agent 接进真实工程，欢迎试用、提 Issue，或者直接拆开看它的 Gate 为什么会拒绝一份看起来已经写完的用例。

项目地址：[github.com/phoenine/Riqor](https://github.com/phoenine/Riqor)

开源协议：[Apache License 2.0](../LICENSE)
