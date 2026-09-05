# Agent-next Development Instructions

These instructions apply to the entire repository.

## Source of truth

- Product and architecture decisions: `docs/agent-next-generalization-v0.1.md`
- Project Profile contract: `schemas/project-profile.schema.json`
- Artifact contract: `schemas/artifact.schema.json`
- Capability contract: `schemas/capability.schema.json`
- Workflow Pack contract: `schemas/workflow.schema.json`
- Automation Provider contract: `schemas/automation-provider.schema.json`

## Implementation rules

1. Reuse Agent-next before implementing. Search the corresponding Workflow,
   Skill, Tool, Template, and tests before adding a new implementation.
   Parameterize existing behavior when possible.
2. Keep Core project-agnostic. Product names, tracks, repositories, platforms,
   and environment policies belong in Project Profiles or Skills; adapters are
   optional thin drivers, not the default integration model.
3. Do not add product-specific tracks, integrations, or repositories as Core
   enums or defaults.
4. Treat knowledge as reusable context and evidence as run-specific support.
5. Any remote write, shared-environment execution, or shared-data mutation must
   remain an explicit confirmation boundary.
6. Add or update tests whenever a schema, semantic rule, or CLI behavior
   changes.
7. Keep workflow capabilities declarative under `workflows/`; do not hard-code
   workflow names in the Core engine.
8. Use repository-relative paths in configuration and generated state.
9. Do not replace the migrated Run State, Stage Gate, template, validator, or
   Skill execution chain without migration-parity tests.

## Verification

Run from the repository root:

```bash
python -m unittest discover -s tests -p 'test_*.py'
python -m tools.agent_next doctor --project examples/shop-platform/project.yaml
```
