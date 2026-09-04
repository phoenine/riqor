# Release Acceptance — Release Baseline

| | |
|---|---|
| **目标** | 锁定待验收的 release bundle、发布类型、覆盖交付线与环境 |
| **输入** | 版本/tag/分支、环境、组件版本、`knowledge/` |
| **产出** | `release_baseline:`；`release_scope_tracks`；`environment.target`；仓库 revision；环境检查 |

**Skills:** `agent-next`, `release-acceptance`

**Repository:** Project Profile product repositories, Project Profile automation repositories

**Environment:** Project Profile environment groups (as needed)

**Gate:** 未锁定版本、环境、Project Profile tracks 和仓库 revision 前，不收集最终范围或跑自动化。一个 release bundle 可覆盖多个项目 track；单个资产仍记录自己的 owning track。

**Machine:** `release_baseline:`; `release_scope_tracks`; `environment.target`; repository evidence — `tools/stage_gate.py`

**Next:** Scope Collection
