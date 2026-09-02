# Feature Testing — Requirement Specification

| | |
|---|---|
| **目标** | 从业务上下文与代码证据产出完整需求规格 |
| **输入** | Phase 1 来源、Project Profile product repositories、`knowledge/` |
| **产出** | `requirement_spec` 产物；来源阅读记录；开放问题列表 |

**Skills:** `requirement-analysis`

**Gate:** 需求规格经确认后再做测试设计。

**Knowledge Prompt:** 若需求规格中的「领域术语」存在“建议补充知识库 =
是 / 待确认”，或 run state 中存在 `knowledge_proposed_updates[]`，完成
需求规格后必须在最终回复中提示用户确认是否更新知识库。未获得明确确认前
不得写入 `knowledge/`。

**Machine:** artifact `requirement_spec` — `tools/stage_gate.py`

**Prev → Next:** Intake → Risk Analysis

Stable, reusable terms or rules discovered here are optional knowledge
proposals. Passing the requirement Gate confirms the artifact only; knowledge
remains `proposed` unless the user explicitly chooses to confirm the requirement
and persist the listed candidates. Existing knowledge pages require separate
review and are not overwritten by this shortcut.
