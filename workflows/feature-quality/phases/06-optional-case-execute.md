# Feature Testing — Optional Case Execute

| | |
|---|---|
| **目标** | 执行已确认的手工或自动化用例（可选） |
| **输入** | 测试设计、环境、Project Profile automation repositories |
| **产出** | `execution_record`；或 `data_injection:`；或 skip |

**Skills:** `automation`, `reporting`; add a Profile-selected data-preparation Skill when needed

**Repository:** Project Profile automation repositories; a Project Profile data-preparation tool repository

**Confirmation before:** automation, shared data mutation, SSH, environment changes.

**Gate:** 须先记录执行证据再报 bug 或结项。

**Machine:** optional; `execution_record` or `data_injection:` or skip — `tools/stage_gate.py`

**Prev → Next:** Optional Case Sync Or Generation → Optional Bug Report
