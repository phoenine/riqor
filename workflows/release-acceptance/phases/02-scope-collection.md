# Release Acceptance — Scope Collection

| | |
|---|---|
| **目标** | 收集并解析本 release bundle 的纳入项、必回归项、Scope Gap 与明确排除项 |
| **输入** | 本版本特性/修复、风险区、测试清单、外部需求与源码平台/发布说明 |
| **产出** | `release_scope:`；`release_scope_tracks`；特性/bug 回归范围；Scope Gap；排除项及理由 |

**Skills:** `release-acceptance`, `requirement-analysis`, `test-analysis` — read `skills/test-analysis/references/test-analysis-methodology.md` when release scope requires risk-based coverage focus.

**Gate:** 须按 Project Profile tracks 归类范围。Tag diff 只能作为 scope initializer，最终范围必须同时对齐 declared release scope、外部需求/问题记录、部署/配置/migration、已知问题与 out-of-scope。差异必须记录为 Scope Gap。

**Machine:** `release_scope:`; `release_scope_tracks` — `tools/stage_gate.py`

**Prev → Next:** Release Baseline → Acceptance Plan
