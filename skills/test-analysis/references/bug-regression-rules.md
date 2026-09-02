# Bug 回归分析规则

用于从问题单、修复 MR、commit 或用户描述生成回归范围、影响分析和覆盖范围审查。

## 回归目标

Bug 回归不只验证“原问题修好了”，还要回答：

- 修改影响了哪些模块、接口、数据、配置、权限或 UI？
- 是否影响相邻功能、共享组件、历史缺陷高发区域？
- 风险、条件和测试点之间是否存在断链或漏覆盖？
- 是否需要补充测试点、测试用例或自动化？

## 必要输入

- Bug 标题、复现步骤、期望/实际、评论/action、解决版本。
- 修复 MR、commit、branch 或可定位的代码变更。
- Project Profile `repositories.product` 映射出的本地 dev repo。
- 相关历史缺陷、知识库、已有手工/自动化覆盖摘要（仅用于判断风险背景；
  具体用例/自动化匹配交给 `test-case-design` / `automation`）。

## 分析顺序

1. Bug Intake：记录 bug 分类、影响模块、原始症状、修复来源、`bug_surface:`（`frontend` / `backend` / `other`）。
2. Change Scope：列 changed files、changed components、affected APIs、DB tables、config。
3. Impact Analysis：识别 API、Database、Cache、Permission、Config、UI、Reports、Statistics、Schedule 等影响域。
4. Test Analysis：按 `test-analysis-methodology.md` 识别适用测试维度、回归条件、风险和测试点。普通回归通常使用 Standard；权限、状态机、多条件规则、跨模块或高风险回归使用 Complex。
5. Coverage Scope Review：检查 original bug、requirement、risk、condition、test point 是否存在断链、漏风险或覆盖缺口。
6. Handoff：把 Test Points / Coverage Gaps 交给 `test-case-design` 做 Coverage Match（Existing TC / Automation 匹配）和后续 Decision。

`test-analysis` 不匹配现有手工用例或自动化覆盖；它只定义和审查“应该覆盖什么”。

## 产物路径

- 所有 bug 回归 Markdown 写入 Project Profile 的 `artifacts.root` 下，按
  bug scope 与 owning track 隔离。
- `bug_surface` 用于风险和覆盖分类，不再决定固定的 Core 输出目录。
- 禁止写入 `runs/<run-id>/`。

## Root Cause Evidence

不要强行猜 root cause。按证据记录：

- `known`：MR、代码或问题单明确说明。
- `unknown`：没有足够证据。
- `not_required`：当前回归只需变更范围和影响覆盖。

## 回归用例质量

好的回归用例应通过正常业务入口复现原症状，并观察修复后的业务结果。

避免把这些作为主要回归用例：

- 纯 API 状态检查，但任务要求 UI 回归。
- 纯前端 disabled/throttle 绑定。
- 只能通过伪造请求、mock 后端 500、断网触发的不可达场景。
