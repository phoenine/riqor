# Bug Regression — Regression Plan

| | |
|---|---|
| **目标** | 定策略与执行/补用例计划 |
| **输入** | Decision、匹配结果与缺口 |
| **产出** | `regression_plan`；`regression_strategy:`；必要时 `test_cases` |

**Skills:** `test-case-design`, `automation`, `reporting`; `automation`
when project-specific test data requires a Profile data-preparation Skill

**Confirmation before:** automation, test-data mutation, test-management update.

**Supplement cases:** When `decision_path: supplement_cases`, use
`copy_template.py --template test-cases`,
`skills/test-case-design/references/test-case-design-methodology.md`,
`skills/test-case-design/references/coverage-review-rules.md`,
`case-writing-rules.md`, then `validate_test_cases.py`.

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template test-cases \
  --producer-phase "Regression Plan" \
  --artifact-id TC-BUG-001 \
  --destination <artifact-root>/<scope>/test-cases/bug-<id>-regression-cases.md
```

**Gate:** 策略、环境、确认项齐备前不执行。

**Machine:** `regression_strategy:`; artifact `regression_plan`; `test_cases` when
`supplement_cases` — `tools/stage_gate.py`

**Prev → Next:** Decision Gate → Execution
