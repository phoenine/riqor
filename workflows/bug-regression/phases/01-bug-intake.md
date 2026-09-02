# Bug Regression — Bug Intake

| | |
|---|---|
| **目标** | 读懂 bug 上下文并锁定修复来源与输出路由 |
| **输入** | Bug ID/问题单、修复 MR/commit、用户描述、`knowledge/` |
| **产出** | `notes[]`: `bug_intake:`, `bug_surface:`；缺失项列表（无 artifact 文件） |

**Skills:** `agent-next`, `requirement-analysis`

**Environment:** `ZENTAO_*` (bug records); `GITLAB_*` (MR/commit metadata)

**Gate:** 未明确 bug 行为、分类、影响模块、修复来源前，不进入 Change Scope。

**Machine:** `bug_intake:`; `bug_surface:`; knowledge — `tools/stage_gate.py`

**Next:** Change Scope
