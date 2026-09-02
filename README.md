# Agent-next

Agent-next is a project-agnostic testing engineering agent workspace. Users
provide the assets they already have and a desired result; Agent-next inventories
the inputs, plans missing dependencies, preserves traceability, and asks before
performing external side effects.

The v0.1 design is documented in
[`docs/agent-next-generalization-v0.1.md`](docs/agent-next-generalization-v0.1.md).
For a verified end-to-end example, see the
[`Shop Platform quickstart`](docs/quickstart-shop-platform.md).
The implementation must also follow the
[`Agent-next reuse alignment audit`](docs/agent-next-reuse-alignment-audit-v0.1.md):
Agent-new reuses and parameterizes Agent-next rather than replacing its proven
Workflow, Skill, Run State, Stage Gate, template, and validator chain.

## Current milestone

R1 through R3 of the reuse-alignment plan are implemented. Agent-new now contains the
proven Agent-next path resolver, phase router, Run State writer/schema/migrator,
template copier, artifact validators, test-case validator, and Stage Gate.
New run state accepts project-defined `project_id` and `tracks`; legacy
`product_line` remains readable during migration and is not a Core enum.

The following Agent-new additions remain retained:

- Project Profiles
- Artifact metadata
- Declarative Capabilities
- Knowledge bootstrap layout
- Artifact inventory and stale propagation
- Scope-aware dependency planning

R2 adds generic `requirement-analysis`, `test-analysis`, `test-case-design`,
`automation`, `reporting`, `release-acceptance`, and `zentao-sync` Skills.
Capabilities now reference their authoritative Workflow, Phase, and Skill;
ePVS-specific automation/data rules remain explicit compatibility extensions.
The secret-free interface and its verification boundary are documented in
[`profiles/epvs/README.md`](profiles/epvs/README.md).
R3 connects `inventory`, `run`, `status`, `explain`, `scaffold`, and `gate` to
that inherited execution chain. Artifact identity, revisions, and traceability
live under `runs/`; `outputs/` contains only user-facing deliverables. No
parallel Adapter SDK or second execution-state model is developed.

## Migrated execution infrastructure

The compatibility commands remain directly runnable behind the unified CLI:

```bash
python3 tools/run_state.py --help
python3 tools/copy_template.py --help
python3 tools/validate_run_state.py --help
python3 tools/stage_gate.py --help
```

For new run state, use Project Profile identity instead of the legacy product
line:

```bash
python3 tools/run_state.py \
  --run-id demo \
  --project-id shop-platform \
  --track storefront \
  --entry feature-quality \
  --phase Intake
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Fill only the local values you need. The CLI reads the root `.env` without
overwriting variables supplied by the current shell or CI. Check names and
presence without exposing values with `agent-next env --group ZENTAO`; see
[`docs/environment.md`](docs/environment.md).

## Validate the example project

```bash
agent-next doctor --project examples/shop-platform/project.yaml
```

Expected result:

```text
OK project shop-platform
OK knowledge index examples/shop-platform/knowledge/_index.md
OK capabilities 17
OK artifact templates 15
```

## Initialize a new project

Create an empty project with the standard knowledge structure:

```bash
agent-next init \
  --project-id my-product \
  --name "My Product" \
  --track web \
  --track backend \
  --default-track backend
```

Register existing background documents during initialization:

```bash
agent-next init \
  --project-id my-product \
  --name "My Product" \
  --source docs/product-prd.md
```

Sources must already exist under the repository root. They are registered in
`knowledge/<project-id>/_sources.yaml` but are not treated as confirmed
knowledge. `init` refuses to overwrite an existing Project Profile or knowledge
root.

Project knowledge is optional for users. `init` creates an empty internal
context skeleton so a new project can start from only a description or PRD.
When requirement work finds stable reusable knowledge, record a proposal file
based on `templates/knowledge/knowledge-proposal.yaml.tmpl`:

```bash
agent-next record \
  --run-id checkout-requirement \
  --knowledge-proposal runs/checkout-requirement/order-timeout.yaml

agent-next knowledge \
  --project examples/shop-platform/project.yaml \
  --run-id checkout-requirement \
  --source-artifact REQ-checkout-001
```

The second command previews names and target paths only. If the user explicitly
chooses “confirm requirement and persist knowledge”, apply those listed
proposals with `--confirm`; confirming the requirement alone leaves them
proposed. Existing knowledge pages are never overwritten by this shortcut.

## Inspect artifacts and plan a goal

Artifact metadata lives under `runs/<run-id>/artifacts/*.json`; `outputs/`
contains only user-facing Markdown deliverables. Each artifact belongs to a
`scope_id`, such as a feature, bug, or release scope.

```text
outputs/<project-id>/features/<requirement-name>/requirement-spec.md
outputs/<project-id>/features/<requirement-name>/risk-analysis.md
outputs/<project-id>/features/<requirement-name>/test-points.md
outputs/<project-id>/features/<requirement-name>/test-cases.md
outputs/<project-id>/bugs/<bug-id-or-name>/regression-report.md
outputs/<project-id>/releases/<version>/acceptance-report.md
```

Artifact IDs and revisions are deliberately absent from user-facing filenames.

```bash
agent-next inventory \
  --project examples/shop-platform/project.yaml \
  --scope checkout

agent-next plan \
  --project examples/shop-platform/project.yaml \
  --workflow feature-quality \
  --scope checkout \
  --goal test_cases
```

The example starts with only a ready PRD. The plan therefore explains the Intake
gate plus four artifact-producing steps needed to reach `test_cases`. When more
than one Workflow Pack is installed, select one with `--workflow <pack-id>`;
Agent-next will not guess between packs. `plan` remains read-only.

## Prepare a run, create an artifact, and validate the phase

Start with the planned Intake gate. This records the authoritative Workflow,
Phase, required Skills, and hash receipts; it does not perform a remote action:

```bash
agent-next run \
  --project examples/shop-platform/project.yaml \
  --workflow feature-quality \
  --capability feature-intake \
  --run-id checkout-requirement \
  --track backend

agent-next record \
  --run-id checkout-requirement \
  --knowledge-plan-status not_needed \
  --knowledge-plan-summary "The current project knowledge is sufficient" \
  --knowledge-used path=skills/requirement-analysis/references/intake-sources.md,purpose=intake \
  --note intake_input:PRD-checkout-001

agent-next gate \
  --project examples/shop-platform/project.yaml \
  --run-id checkout-requirement
```

After Intake passes, move the same Run State to the first artifact-producing
step and scaffold its declared template:

```bash
agent-next run \
  --project examples/shop-platform/project.yaml \
  --workflow feature-quality \
  --capability requirement-specification \
  --run-id checkout-requirement \
  --track backend

agent-next scaffold \
  --project examples/shop-platform/project.yaml \
  --workflow feature-quality \
  --capability requirement-specification \
  --scope checkout \
  --artifact-id REQ-checkout-001 \
  --run-id checkout-requirement \
  --source-artifact PRD-checkout-001@1 \
  --track backend
```

Fill the generated Markdown, update the Run State evidence required by the
Workflow phase, then validate it:

```bash
agent-next gate \
  --project examples/shop-platform/project.yaml \
  --artifact-id REQ-checkout-001 \
  --run-id checkout-requirement \
  --mark-ready
```

`scaffold` delegates to the inherited managed template copier and registers the
artifact in the same Run State. `gate` delegates to the artifact-type validator
and strict Stage Gate. It refuses ready when the template is untouched or still
contains placeholders, upstream
revisions changed, sources are not ready, the predecessor phase has not passed,
or required knowledge/repository/confirmation evidence is missing. A successful
ready transition records the deliverable SHA-256; Inventory marks it stale if
the content later changes.

Inspect the live state and the reason for every blocker:

```bash
agent-next status --run-id checkout-requirement
agent-next explain --run-id checkout-requirement
```

## Run tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Repository map

```text
config/               Project Profile registrations
knowledge/            Reusable knowledge, isolated by project
profiles/             Reusable project presets
workflows/            Declarative workflow capabilities
skills/               Agent-facing workflow instructions
templates/            Managed .md.tmpl sources for knowledge and artifacts
schemas/              Public JSON Schema contracts
tools/                Core engine, validators, state tools, and CLI
repositories/         Local product, automation, and tool repository mirrors
outputs/              Generated deliverables, isolated by project
runs/                 Durable execution state
examples/             Runnable example projects
docs/                 Product and architecture documentation
tests/                Unit and contract tests
```

The repository is the runtime boundary. Core code intentionally lives in
`tools/`; there is no separate `src/agent_next/` package tree. An editable
install only provides the `agent-next` command for this checkout.
