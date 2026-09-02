# Run State

Run state is the durable memory for one `agent-next` workflow run. It lets
stage gates verify work from files instead of relying on conversation memory.

Default location:

```text
runs/<run-id>/state.json
```

Schema:

```text
schemas/run-state.schema.json
```

The current contract is `schema_version: 2`. Historical files without this
field are treated as legacy v1, but ordinary writers will not upgrade them
implicitly.

Validate a run state file against the schema plus semantic rules (canonical
phase names per entry):

```bash
python3 tools/validate_run_state.py \
  --state runs/<run-id>/state.json \
  --schema schemas/run-state.schema.json
```

`--schema` defaults to `schemas/run-state.schema.json`. JSON Schema checks run
through `jsonschema` (see `requirements.txt`). Semantic checks then apply:

- canonical phase names per entry (`tools/phases.py`, reported as `$.phase:`)
- global run-state rules shared with `tools/stage_gate.py` (router skill
  `agent-next`, skill receipts, `knowledge_plan`, environment groups,
  confirmations, artifact metadata)

Phase-specific gate rules still require `tools/stage_gate.py` with the current
`entry` and `phase`.

## Versioning And Migration

Audit every historical state without modifying it:

```bash
python3 tools/migrate_run_state.py \
  --runs-root runs \
  --output runs/<audit-run-id>/run-state-migration-report.json
```

The report separates schema blockers from post-migration semantic validation
warnings. Automatic changes are intentionally limited to transformations that
preserve evidence:

- add the current `schema_version`;
- normalize recognized legacy workflow paths;
- rewrite an absolute skill receipt path only when its recorded sha256 matches
  the corresponding repository skill file.

The bulk form is dry-run only. Migrate one reviewed, schema-ready file with an
explicit write:

```bash
python3 tools/migrate_run_state.py \
  --state runs/<run-id>/state.json \
  --write
```

Before replacement, the tool creates a timestamped sibling backup such as
`state.json.v1.<timestamp>.bak`. Structural ambiguity remains a blocker; the
tool does not invent missing evidence, receipt hashes, artifact metadata, or
knowledge classifications.

## Required Fields

| Field | Purpose |
|---|---|
| `schema_version` | Run-state contract version. Must be `2` for current writers and gates. |
| `run_id` | Stable run identifier. |
| `product_line` | Product line for single-asset routing and output decisions. Must be `v1` or `v2`. |
| `release_scope_tracks` | Release bundle coverage for release acceptance. Values may include `v1`, `v2`, and `shared`. |
| `entry` | One of `feature-quality`, `bug-regression`, or `release-acceptance`. |
| `workflow` | Selected workflow file path. |
| `phase` | Current workflow phase. |
| `required_skills` | Skills required by the current phase. |
| `loaded_skills` | Skills actually loaded for the current phase. |
| `skill_receipts` | Skill files actually read, with path and sha256. |
| `repositories` | Local dev, test, and tools repository records. |
| `repository_evidence` | Files, commits, diffs, symbols, or commands actually inspected. |
| `knowledge_used` | Knowledge files and required skill references that supported conclusions. |
| `knowledge_plan` | Whether supplemental knowledge is needed (`pending`, `not_needed`, `proposed`, `confirmed`, or `rejected`) plus summary and evidence. |
| `knowledge_proposed_updates` | Draft knowledge changes awaiting user confirmation before writing into `knowledge/`. |
| `environment` | Required and checked `.env` groups plus target environment. |
| `confirmations` | User confirmations for side-effect actions. |
| `artifacts` | Produced artifacts with minimal metadata. |
| `traceability` | Links between upstream and downstream artifact IDs. |
| `notes` | Structured evidence strings (for example `intake_input:`, `data_injection:`, `optional_skip:<phase>:`). |
| `gate_results` | Stage gate check results. |

## Optional Knowledge Proposals

A new project does not need existing knowledge content. `init` creates an empty
internal context skeleton, and a phase with no relevant knowledge records
`knowledge_not_applicable:`.

When a confirmed requirement contains stable reusable domain knowledge, create
a proposal from `templates/knowledge/knowledge-proposal.yaml.tmpl` and record it:

```bash
agent-next record \
  --run-id <run-id> \
  --knowledge-proposal runs/<run-id>/<proposal>.yaml
```

This stores `status=proposed` only. After the requirement artifact passes its
Gate, preview the candidates with `agent-next knowledge`. If the user chooses
“confirm requirement and persist knowledge”, rerun with `--confirm` and the
requirement artifact ID. “Confirm requirement only” performs no knowledge
write. The shortcut creates new pages only and never overwrites an existing
knowledge file.

## Canonical Phases

`phase` must use the exact workflow phase names from `tools/phases.py` (also listed
in each `workflows/<entry>/README.md`). Tools
normalize common drift such as `intake` → `Intake`, but the canonical spellings
below are the source of truth. Authoritative list: `tools/phases.py`.

### feature-quality

- `Intake`
- `Requirement Specification`
- `Risk Analysis`
- `Test Design`
- `Optional Case Sync Or Generation`
- `Optional Case Execute`
- `Optional Bug Report`
- `Optional Test Report`

### bug-regression

- `Bug Intake`
- `Change Scope`
- `Impact Analysis`
- `Coverage Match`
- `Decision Gate`
- `Regression Plan`
- `Execution`
- `Regression Report`

### release-acceptance

- `Release Baseline`
- `Scope Collection`
- `Acceptance Plan`
- `Acceptance Execution`
- `Release Decision`
- `Optional Post-release Observation`

Record phase changes through `run_state.py` so names stay canonical:

```bash
python3 tools/run_state.py \
  --run-id feature-login-20260708 \
  --entry feature-quality \
  --phase intake
```

The CLI stores `Intake` in `state.json`.

## Evidence Rules

- `repositories` records where a repo is and which branch/tag/commit or working
  tree state was used.
- `repository_evidence` records what was actually inspected.
- `knowledge_used` records knowledge and required skill-reference files that
  supported a conclusion. Do not record unused material just because it was read.
- `artifacts[*].source_artifacts` and `traceability` keep the chain from
  requirement to report.

Record evidence through `tools/run_state.py` instead of editing `state.json` by
hand (run from this repository root):

```bash
python3 tools/run_state.py \
  --run-id feature-login-20260708 \
  --repository kind=dev,name=newepvs-demo,path=repositories/dev/newepvs-demo,commit=abc123 \
  --repository-evidence repo=newepvs-demo,evidence_type=file,reference=src/App.tsx,supports=REQ-001 \
  --knowledge-used path=knowledge/epvs/_index.md,purpose=术语确认 \
  --knowledge-plan-status not-needed \
  --knowledge-plan-summary "未发现需要补充的领域知识。" \
  --knowledge-plan-evidence knowledge/epvs/_index.md \
  --trace from=REQ-001,to=RISK-001,relation=drives
```

Use `--knowledge-plan-status proposed` with `--knowledge-proposed-update
path=knowledge/...,summary=...,status=proposed` when a workflow
finds knowledge that should be reviewed before it becomes durable knowledge.

## Product Line Rules

Record `product_line` before selecting repositories or writing artifacts.

- Use `v1` for the legacy ePVS product line.
- Use `v2` for the current ePVS product line.
- If the product line is unclear, ask before creating downstream artifacts.

For release acceptance, `product_line` is not the release scope. It remains the
owning line of a single artifact for compatibility. Record the release bundle
coverage separately:

```bash
python3 tools/run_state.py \
  --run-id release-2.8.0 \
  --entry release-acceptance \
  --phase "Release Baseline" \
  --product-line v2 \
  --release-scope-track v1 \
  --release-scope-track v2 \
  --release-scope-track shared
```

Release-level artifacts belong under `outputs/releases/<release>/`; referenced
feature, bug, test point, test case, and automation assets stay under their
owning `outputs/v1/`, `outputs/v2/`, or `outputs/shared/` paths.

## Skill Receipt Rules

Record a receipt for every required skill after reading its `SKILL.md`:

```bash
python3 tools/run_state.py \
  --run-id feature-login-20260708 \
  --product-line v2 \
  --required-skill agent-next \
  --loaded-skill agent-next \
  --skill-receipt agent-next=skills/agent-next/SKILL.md
```

The tool records the skill path and sha256 in `skill_receipts[]`. Stage gates
must use receipts to verify skill loading, not only `loaded_skills`.

## Artifact Creation

Create Markdown artifacts from `templates/` with
`tools/copy_template.py`. Do not create blank artifact files by hand.

Example:

```bash
python3 tools/copy_template.py \
  --run-id feature-login-20260708 \
  --template requirement-spec \
  --producer-phase "Requirement Specification" \
  --artifact-id REQ-SPEC-001 \
  --source-artifact feishu:doc-001 \
  --evidence zentao:story-001 \
  --destination outputs/v2/requirements/requirement-spec.md
```

When the run state exists, the tool also records the artifact under
`artifacts[]` with metadata required by the stage gate.

Use `runs/<run-id>/` for durable run state and gate records. Use
`outputs/v1/`, `outputs/v2/`, `outputs/shared/`, and
`outputs/releases/<release>/` for deliverable artifacts.

## Confirmation Rules

Use `confirmations` before actions with side effects:

- ZenTao write actions.
- ZenTao acceptance test order creation, update, or case association changes.
- Bug create/update/close actions.
- Shared test data mutation.
- Automation execution in shared or production-like environments.
- SSH or environment changes.
- Shared knowledge updates.

The stage gate must fail when a required confirmation is missing or rejected.

Record confirmations through run state:

```bash
python3 tools/run_state.py \
  --run-id feature-login-20260708 \
  --confirmation id=sync-zentao,action=zentao-upload,status=required
```

## Gate Results

Run stage gates by state path or run id. The gate writes the latest result back
to `gate_results[]` unless `--no-write` is used:

```bash
python3 tools/stage_gate.py \
  --run-id feature-login-20260708 \
  --entry feature-quality \
  --phase "Requirement Specification"
```

## Minimal Example

```json
{
  "schema_version": 2,
  "run_id": "feature-login-20260708",
  "product_line": "v2",
  "entry": "feature-quality",
  "workflow": "workflows/feature-quality/README.md",
  "phase": "Intake",
  "required_skills": ["agent-next", "epvs-requirement"],
  "loaded_skills": ["agent-next", "epvs-requirement"],
  "skill_receipts": [],
  "repositories": {
    "dev": [],
    "test": [],
    "tools": []
  },
  "repository_evidence": [],
  "knowledge_used": [],
  "knowledge_plan": {
    "status": "pending",
    "summary": "",
    "evidence": []
  },
  "knowledge_proposed_updates": [],
  "environment": {
    "required_groups": ["ZENTAO", "GITLAB"],
    "checked_groups": [],
    "target": "test"
  },
  "confirmations": [],
  "artifacts": [],
  "traceability": [],
  "gate_results": []
}
```
