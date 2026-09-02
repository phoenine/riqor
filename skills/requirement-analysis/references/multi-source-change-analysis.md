# 多源变更分析

用于一个特性或问题跨多个仓库、多个来源时，将 PRD、禅道、GitLab MR、commit 和本地源码合并成统一需求或影响说明。

## 典型场景

- 前端 MR 与后端本地 commit 共同实现一个功能。
- 禅道 task/story 只写业务目标，实际变更散落在多个服务。
- 一个 Bug 修复同时涉及 UI、API、权限、数据处理或公共库。
- release scope 需要从多个 GitLab 项目和本地 repo 合并。

## 分析顺序

1. 记录 `project_id` 和适用 `tracks`。
2. 用 Project Profile 解析远端项目与本地 product repository。
3. 按来源分别收集证据：
   - PRD/禅道：业务目标、验收标准、用户可见行为。
   - GitLab MR/commit：变更文件、描述、关联 issue/task、pipeline。
   - 本地 dev repo：真实 diff、代码路径、接口、UI、数据口径。
4. 合并成统一的功能边界、用户路径、API/数据约束和风险入口。
5. 输出 open questions，不用猜测补齐缺口。

## 合并判断

| 来源 | 主要价值 |
|---|---|
| 需求/PRD | 业务意图和验收目标 |
| 禅道 task/story/bug | 组织上下文、模块、状态、历史行为 |
| 前端变更 | 用户入口、页面状态、交互、可观察结果 |
| 后端变更 | 权限、校验、数据口径、接口契约、状态机 |
| 公共库变更 | 跨模块回归影响 |

## 输出要求

- 需求说明必须列出所有已确认来源和未确认来源。
- 代码证据进入 `repository_evidence`。
- 多仓库结论要写清哪个 repo 支撑哪个行为。
- 下游风险和测试点不要把前后端编号混在同一个含义里；用稳定前缀或 artifact ID 保持可追溯。
