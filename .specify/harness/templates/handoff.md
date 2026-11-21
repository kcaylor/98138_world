# Handoff

Fill providers, limits and milestones, then run `speckit-harness handoff pin --feature specs/NNN-name`.
Commit the spec/plan/tasks first (S). Commit this generated contract alone next (H).
H is recorded outside this file. Never put the containing commit's hash inside the contract.

```handoff-json
{
  "providers": {"planner": "claudeAgent", "implementer": "codex", "reviewer": "claudeAgent"},
  "limits": {"review_rounds": 2, "dispatch_attempts": 2},
  "milestones": [{"id": "M1", "tasks": ["T001"], "exit": ["REPLACE with the project's validation command"]}],
  "supersedes": null
}
```

## Scope for the implementer

Describe the expected changes and exclusions. The pinned spec, plan and tasks are authoritative.

## Reserved decisions

Apply the project's constitution and run policy, subject to inherited platform and user instructions.

## Milestone evidence

Report the full implementation commit and the results of the milestone's exit commands.
