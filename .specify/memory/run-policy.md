# Run policy

Copy to `.specify/memory/run-policy.md` and edit. `speckit-run` reads this file at the start of every
run. It overrides the skill's default escalation lists. The constitution overrides this file.

## Always ask me

- Product scope: what is in or out of a feature.
- Data migrations, schema changes, or anything that deletes data.
- Changes to public APIs, CLI flags, or file formats other people use.
- Authentication, secrets, and personal data handling.
- New third-party services or dependencies with non-permissive licenses.
- <add project-specific items>

## Decide and log

- Choices that follow an existing pattern in the codebase.
- Defaults for unstated non-functional details (timeouts, page sizes, log levels).
- Internal structure, task order, and refactoring inside the feature's scope.
- <add project-specific items>

## Run settings

- Maximum questions per stop: 6
- Clarify rounds before moving on: 2
- Attempts per failing task before marking it blocked: 3
- Commit when done: no
- Open a pull request when done: no

<!-- Optional; uncomment only to opt this project in. Installing the harness does not enable it.
## Agent roles
- paired: default
- planner: claudeAgent
- implementer: codex
- reviewer: claudeAgent
-->
