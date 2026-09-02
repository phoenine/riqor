# 版本源码同步规则

用于 release acceptance 中按版本 tag 锁定本地源码，并基于该源码生成验收计划、pages/cases 或报告。

## 核心规则

- Agent 自己同步本地源码，不要求用户逐仓库手动 pull。
- 版本验收以 tag 语义为准：锁定 `refs/tags/<tag>`，不是同名 branch。
- 如果同名 branch 和 tag 同时存在，仍以 tag 为准。
- 不要在 detached HEAD 上执行 `git pull`。
- 保留未跟踪的 `.zread/`、`docs/` 等知识或说明目录，不要清理。

## 推荐流程

对 Project Profile `repositories.product` 映射出的相关 dev repo 执行：

```bash
git fetch --tags --force --prune origin
git checkout refs/tags/<tag>
git rev-parse --short HEAD
git branch --show-current
git describe --tags --exact-match
git status --porcelain
```

期望结果：

- `git describe --tags --exact-match` 返回目标 tag。
- `git branch --show-current` 为空，表示 detached HEAD。
- 工作区若有未跟踪知识/文档目录，需要记录但不删除。

## 写验收资产前

- 先读当前 pages/cases 或已有验收资产。
- 先读 `templates/` 对应模板。
- 从 tag checkout 的源码读取真实文件和行段。
- 知识库只作业务语义支持，不能作为唯一风险证据。

## 写验收资产后

- 检查源码证据路径不带旧本地根目录前缀。
- 检查证据路径存在，行号未越界。
- 检查 pages/cases 的 ID 引用未悬空。
- 新生成并计划上传的用例默认标记未同步，不保留过期外部 ID。
- 把 repo、tag、commit、文件证据写入 run state。
