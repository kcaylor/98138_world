---
name: speckit-derive-constitution
description: Create or audit the Spec Kit constitution (.specify/memory/constitution.md). Derives principles from an existing codebase with cited evidence, or interviews the user when the project is new. Use when the constitution is missing or still holds template placeholders, when the user asks to set up, draft, derive, or audit project principles, or when speckit-run finds no usable constitution.
---

# Derive a Spec Kit constitution

This skill produces the content of a project constitution. It does not write the file itself. Writing,
versioning, template resolution, and the Sync Impact Report are handled by the installed
`speckit-constitution` skill, which this skill calls at the end with the gathered principles as its
input.

The constitution is the user's governance document. Every principle in it must come from one of two
sources: evidence in the repository that the user confirms, or an answer the user gives. Never
invent a principle because it seems like good practice.

## Step 1. Determine the mode

Read `.specify/memory/constitution.md`.

- **Missing, or still a template.** The file counts as a template if it contains any
  `[ALL_CAPS_TOKEN]` placeholder such as `[PROJECT_NAME]` or `[PRINCIPLE_1_NAME]`. `specify init`
  copies the unfilled template into place, so the file existing is not enough.
- **Filled.** No placeholders remain. Go to Mode C (audit).

For a missing or template constitution, decide whether the project has enough existing material to
derive from. Count it as an **existing project** if at least two of the following hold:

- source files outside `.specify/`, `.claude/`, `.agents/`, and `specs/`
- a package manifest or build file (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`,
  `Makefile`, and similar)
- a test directory or test configuration
- CI configuration (`.github/workflows/`, `.gitlab-ci.yml`, and similar)
- more than a handful of commits in `git log`

Existing project: Mode A. Otherwise: Mode B.

## Mode A. Derive from the existing project

### A1. Collect evidence

Read these sources where they exist. Keep a list of file paths for each finding.

| Area | Where to look |
|---|---|
| Purpose and scope | README, docs/, project description in the manifest |
| Agent and contributor rules | AGENTS.md, CLAUDE.md, CONTRIBUTING.md, .github/ templates, CODEOWNERS |
| Languages and stack | manifests, lockfiles, Dockerfiles, infrastructure files |
| Code standards | linter and formatter configs, type-checker settings and strictness, editorconfig, pre-commit |
| Testing | test layout, coverage config and thresholds, test commands in CI, ratio of test files to source files |
| Quality gates | CI workflows: which checks block merges |
| Architecture | top-level layout, module boundaries, ADRs or design docs, public API surfaces |
| Dependencies | how many, pinning policy, vendoring, license files |
| Security and data | SECURITY.md, secret-scanning config, handling of credentials, any data-privacy notes |
| Versioning and release | CHANGELOG, tags, release workflows, semver usage |
| Observability | logging setup, metrics or tracing libraries |
| Working conventions | commit message style and branch naming, from `git log --oneline -50` |

Do not read the whole codebase. Sample enough source files to confirm a pattern, then stop.

### A2. Draft candidate principles

Turn the evidence into 4 to 8 candidate principles plus the additional sections the template asks
for (constraints, development workflow, governance). Each candidate needs:

- a short name and a rule stated with MUST or SHOULD
- a one-line rationale
- the evidence paths that support it
- a confidence level:
  - **High**: enforced by tooling or CI, or stated in a rules file (for example, CI fails when
    coverage drops below 80%)
  - **Medium**: a consistent pattern with no enforcement (for example, every module has a matching
    test file, but CI does not check this)
  - **Low**: partial or conflicting evidence, or a matter of intent the code cannot show

Also record **gaps**: areas the template expects where the repo gives no evidence (often
governance, security posture, and performance targets).

### A3. Ask only what the evidence cannot answer

Collect questions into one batch of at most 6. Ask about:

- every Low-confidence candidate
- conflicts, where the code does one thing and a document says another
- aspirations: whether a Medium pattern should become a rule (MUST), a preference (SHOULD), or stay
  out of the constitution
- gaps that matter for later phases, especially testing discipline, security and data handling,
  and how amendments are approved

For each question give a recommended answer and the evidence behind it, so the user can accept it
with one word. Use the question format described under "Asking questions" below.

Do not ask about High-confidence items one by one. List them in the draft for confirmation.

### A4. Confirm the draft

Present the full draft in one message: principles grouped by confidence, with evidence paths, plus
the answers from A3 folded in. Ask the user to approve, edit, or strike items. One round of edits is
normal; if the user asks for more, repeat until they approve.

Then go to Step 2.

## Mode B. Interview for a new project

Ask in rounds of 3 to 5 questions. Offer a recommended default for each so the user can reply
"defaults" for a whole round. Skip any question the user has already answered in conversation or
that an existing file answers.

**Round 1: purpose and constraints**
1. What is the project, and who uses it?
2. What languages, frameworks, or platforms are fixed? What is ruled out?
3. What deployment target and environments are expected (local tool, web service, library, data
   pipeline, mobile app)?
4. Are there regulatory, data-privacy, or institutional constraints?

**Round 2: engineering discipline**
5. Testing: test-first required, tests required with each change, or tests encouraged? Is there a
   coverage floor?
6. How strict should typing, linting, and formatting be, and should CI enforce them?
7. Dependency policy: prefer the standard library, allow freely, or require justification for each
   new dependency?
8. What matters most when tradeoffs arise: simplicity, performance, flexibility, or something else?

**Round 3: interfaces and operations**
9. Are there public interfaces (API, CLI, file formats, library API) that need stability or
   versioning rules?
10. What logging, error-handling, or observability expectations apply?
11. How should security-sensitive code (auth, secrets, user data) be handled and reviewed?

**Round 4: governance and agent behavior**
12. Who can amend the constitution, and does an amendment need a written rationale?
13. Which decisions must agents always bring to you rather than make themselves?
14. Anything else that is non-negotiable?

Stop early when the answers already cover the template. After the last round, present the draft as
in A4 and get approval.

Question 13 also feeds `speckit-run`. If the user answers it, offer to write the answer to
`.specify/memory/run-policy.md` in addition to the constitution.

## Mode C. Audit an existing constitution

1. Read the constitution and collect evidence as in A1.
2. Report drift in both directions: rules the code or CI no longer follows, and strong enforced
   patterns the constitution does not mention.
3. If there is no drift, say so and stop. Do not rewrite a constitution that is still accurate.
4. If there is drift, propose specific amendments with evidence and ask the user to approve each
   one. Only approved amendments go to Step 2.

## Step 2. Write through speckit-constitution

Call the installed `speckit-constitution` skill with the approved content as its input.

- Claude Code: invoke the skill `speckit-constitution`.
- Codex: invoke `$speckit-constitution`.
- Any other agent, or when skill-to-skill invocation is not available: read
  `.specify/harness/commands/speckit.constitution.md` and follow it directly.

Pass the input as plain text: project name, each principle with its rule and rationale, the
additional sections, governance rules, and the ratification date. For a new constitution, the
ratification date is today. For an existing project that had no constitution, it is also today,
unless the user names another date. Leave out the evidence paths and confidence levels; they are for
the user's review, not for the constitution.

After it finishes, report the version written and any `TODO(...)` items it left, and suggest a
commit message. Do not commit unless the user asks.

## Asking questions

- Batch questions. Never ask one question, wait, and then ask the next when they could have gone
  together.
- Each question states what is being decided, why it matters for later phases, and a recommended
  answer.
- Claude Code: use the structured question tool (AskUserQuestion) when available, with the
  recommended option listed first.
- Codex and any other agent: end the turn with a numbered list of questions. Resume from the user's reply.

## Rules

- Write only `.specify/memory/constitution.md`, and only through `speckit-constitution`. The optional
  `run-policy.md` is the one exception, and only with the user's approval.
- Do not add principles the user has not approved.
- Keep principles testable. Replace vague words such as "robust" or "clean" with a rule that a
  reviewer or a CI check could verify.
