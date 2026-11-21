# .specify/harness

Managed by speckit-harness 1.1.0. Do not edit files here; run `speckit-harness ensure` to
refresh them. Project-specific settings belong in `.specify/memory/run-policy.md`.

- `skills/` holds the canonical harness skills. Agents that load skills get copies in their own
  skills folder; any other agent reads these files directly.
- `commands/` holds Spec Kit's phase instructions in a form any agent can follow
  (`speckit.specify.md`, `speckit.plan.md`, and so on).
- `agents` lists the agents this project is set up for.
- `VERSION` is the harness version installed here.

- `templates/handoff.md` is the draft contract for opt-in `speckit-pair` runs.
