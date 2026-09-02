# Bug Regression — Execution

| | |
|---|---|
| **目标** | 执行已确认的计划 |
| **输入** | Regression Plan、环境、Project Profile automation repositories |
| **产出** | `execution_record` 或 `data_injection:`；或 `optional_skip:Execution:` |

**Skills:** `automation`, `reporting`; `automation` when needed.

**Repository:** Project Profile automation repositories; a Project Profile data-preparation tool repository for data setup.

**Confirmation before:** automation, shared data mutation, SSH, environment changes.

**API verification:** Confirm the selected track; trace path from user curl/browser — see
`agent-next` Pitfalls.

**Gate:** 在范围内须先记录执行证据；范围外须先 `optional_skip:Execution:`。

**Machine:** optional; `execution_record` or `data_injection:` or skip —
`tools/stage_gate.py`

**Prev → Next:** Regression Plan → Regression Report
