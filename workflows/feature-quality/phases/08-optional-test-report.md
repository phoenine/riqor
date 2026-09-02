# Feature Testing — Optional Test Report

| | |
|---|---|
| **目标** | 产出特性测试结项报告（可选） |
| **输入** | 需求、测试设计、执行/bug 记录（如有） |
| **产出** | `run_summary` 产物；traceability；跟进项 |

**Skills:** `reporting`

```bash
python3 tools/copy_template.py \
  --run-id <run-id> \
  --template run-summary \
  --producer-phase "Optional Test Report" \
  --artifact-id RUN-SUMMARY-001 \
  --destination <artifact-root>/<scope>/reports/<feature>-run-summary.md
```

**Skip:** `optional_skip:Optional Test Report: <reason>`

**Machine:** optional; `run_summary`; traceability or skip — `tools/stage_gate.py`

**Prev:** Optional Bug Report
