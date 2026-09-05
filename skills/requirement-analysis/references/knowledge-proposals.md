# Knowledge Proposal Contract

Read this reference only when a requirement identifies a stable reusable term,
rule, formula, entity relationship, or long-lived contract that is missing or
changed in Project knowledge.

1. Mark the affected item in `领域术语` or `待确认问题`.
2. Record a proposal with `agent-next record --knowledge-proposal`; keep its
   status `proposed`.
3. Ask the user to choose between confirming only the requirement and also
   persisting the listed knowledge proposals.
4. Requirement Gate success alone does not confirm knowledge.
5. Only after explicit combined confirmation, use
   `agent-next knowledge --confirm --source-artifact <requirement-id>`.
6. Never overwrite an existing knowledge page without separate content review.
