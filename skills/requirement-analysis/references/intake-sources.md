# 入口来源与连通性

用于把飞书文档、禅道 task/story/bug、GitLab MR、本地说明转换为
`agent-next` workflow 的 intake 输入。

## 来源优先级

| 来源 | 应读取内容 |
|---|---|
| 飞书 PRD | 文档正文、标题、章节、验收标准、未决问题 |
| 禅道 task | 关联 story、描述、评论/action、MR 链接、负责人、状态 |
| 禅道 story | `spec`、`verify`、关联 task、fromBug、模块、版本 |
| 禅道 bug | 标题、复现步骤、期望/实际、评论/action、解决版本、关联 story/task |
| GitLab MR | 描述、diff、commit、关联禅道 ID、pipeline 状态 |
| 本地说明 | 用户给出的 Markdown、截图说明、口头范围 |

## Agent-next 规则

- 先记录 `project_id` 和适用 `tracks`，再选择项目映射。
- 用 Project Profile 从远端项目或仓库路径解析本地 product repository。
- 优先读取 Profile 声明的本地仓库；只有本地镜像缺失、过期或需要 MR 元数据时才调用远端平台。
- 读取知识库后，只把真正支撑结论的文件写入 `knowledge_used`。
- 若 track、项目、模块或代码仓库无法确定，记录 open question，不要猜。

## 连通性检查

进入依赖外部系统的 phase 前，按实际来源检查环境组：

- 文档、测试管理和源码平台所需环境组由 Project Profile 或选中的
  integration Skill 声明。

连通性失败时不要继续生成下游测试资产；先记录阻塞原因。

## 需求归档要点

- 原始业务目标和用户可见行为。
- 禅道 ID、飞书文档、MR、commit 的来源引用。
- 受影响模块、接口、页面、数据表或配置。
- 源码阅读范围和结论。
- 待确认问题。
- 是否需要知识库补充；需要时只提 proposal，等待确认。
