---
name: speckit-run
description: Run the full Spec Kit workflow (constitution check, clarify, plan, tasks, analyze, implement, converge) against an existing specification file without the user issuing each command. If no specification exists, drafts one from the user prompt after asking the user up to four questions. Resolves questions from the repository where it can and escalates only the decisions its policy reserves for the user. Use when the user points to a spec to build, says "run speckit" or "build this spec", describes a feature to build with Spec Kit, or asks to resume a feature already in progress.
---

# Run the Spec Kit workflow

This skill runs the installed Spec Kit phase skills (`speckit-specify`, `speckit-plan`, and so on) in
order. It does not reimplement them. Its job is to decide what happens between phases: which
questions it can answer itself, which ones go to the user, and when to stop.

The primary input is a specification the user has already developed. Drafting a new specification
from a prompt is a fallback, and it always requires the user's input (Step 2B).

The user should only need to (1) point to the spec, or describe the feature and answer up to four
scoping questions, (2) answer escalated questions, and (3) review the result.

## Invoking a phase

- Claude Code: invoke the skill `speckit-<phase>` and pass arguments as its input.
- Codex: invoke `$speckit-<phase>` with the arguments.
- Any other agent, or when skill-to-skill invocation is not available: read
  `.specify/harness/commands/speckit.<phase>.md` (for example `speckit.plan.md`) and follow it
  directly, treating the arguments as its user input. These files work for every agent.

If the session supports subagents, run each of specify, plan, tasks, analyze, and each implement
batch in a fresh subagent. Give the subagent the feature directory, the phase to run, the arguments,
and this skill's escalation rules. Ask it to return a summary of 20 lines or fewer: files written,
decisions made, and open questions. Keep full phase output out of the main thread.

## Paired feature routing

If the selected `specs/<feature>/handoff.md` exists, or an uncommented `## Agent roles` section
in run-policy.md sets `paired: default`, stop this workflow and defer to
`speckit-pair` before ensure or any phase can edit pinned files. Do not create or update
run-state.md for paired runs. A delegated paired worker follows its pinned milestone brief and
verifies the contract; it does not recursively invoke the coordinator skill. A delegated planner
uses the individual planning phase instructions directly, without repeating this routing.

## Step 0. Load policy and state

1. **Policy.** Read `.specify/memory/run-policy.md` if it exists. It overrides the defaults under
   "Escalation policy" below. If it does not exist, use the defaults.
2. **State.** Find the feature directory. For a new feature it does not exist yet. For a resume, look
   for `specs/*/run-state.md` on the current branch, or use the directory the user names. If
   `run-state.md` exists, read it, apply any answers the user has just given, and continue from the
   recorded phase.
3. **Preflight.** Run this in the repository root and follow its output before continuing:

       speckit-harness ensure --agent <your Spec Kit integration key>

   It installs or refreshes Spec Kit and this harness for your agent, and checks for updates. If the
   command is not found, see the harness block in AGENTS.md for how to install it on this machine.

## Step 1. Constitution gate

If `.specify/memory/constitution.md` is missing or still contains `[ALL_CAPS]` template
placeholders, run the `speckit-derive-constitution` skill before anything else. This phase is always
interactive. The run never approves constitutional principles on the user's behalf.

After the constitution exists, read it once and keep its principles in view for every later
decision.

## Step 2. Establish the specification

Resolve the target in this order and use the first that applies.

1. **A path the user gives.** The user names a file (for example `specs/004-export/spec.md` or
   `docs/export-feature.md`).
2. **A spec on the current branch.** The branch matches a feature directory in `specs/` and that
   directory has a `spec.md`.
3. **A spec the user refers to by name.** Search `specs/*/spec.md` and `docs/` for a title or
   directory name that matches. If more than one matches, ask the user which one; do not guess.
4. **None of the above.** Use the fallback in 2B.

### 2A. Existing specification (primary path)

**If the file is a Spec Kit spec** (a `spec.md` inside a `specs/<NNN-name>/` directory):

- Adopt that directory as the feature directory and check out its branch if it is not current.
- Do not run `speckit-specify`. The spec is the user's work. Do not rewrite or restructure it.
- Check it against the spec template: user stories with priorities, functional requirements,
  success criteria, and key entities where relevant. Record missing sections as clarify items for
  Step 3; do not fill them in here.
- Collect every `[NEEDS CLARIFICATION: ...]` marker into the question queue for Step 3.

**If the file is a specification outside Spec Kit** (a design doc, PRD, or notes file):

- Run `speckit-specify` with this input: "Convert the specification in `<path>` into a Spec Kit
  spec. Preserve every requirement, constraint, and decision it states. Do not add scope. Where
  the source is silent, insert `[NEEDS CLARIFICATION]` markers rather than inventing detail."
- Afterwards, compare the new `spec.md` with the source file. Every requirement in the source must
  appear in the spec. Fix omissions before continuing. Record the source path at the top of
  `run-state.md`.
- Collect `[NEEDS CLARIFICATION]` markers into the question queue for Step 3.

Because the user wrote or approved this specification, Step 3 treats a conflict between the spec
and the codebase or constitution as a reserved decision. The agent does not resolve such a
conflict by editing the spec.

### 2B. No specification (fallback)

Drafting a specification requires the user's input. Do not draft one from the prompt alone, even
if the prompt seems complete.

1. Read the prompt, the constitution, and the relevant parts of the codebase. Decide what is still
   unknown and would most change the spec.
2. Ask the user **at most four questions**, in one batch (see "Asking the user"). Choose from these
   areas, in priority order, and skip any the prompt already answers:
   - **Outcome:** what problem the feature solves and for whom, and how the user will know it works
     (success criteria).
   - **Scope:** the most important user journey, and what is explicitly out of scope for this
     version.
   - **Constraints:** data, integrations, platforms, or deadlines that limit the design.
   - **Priority:** if the feature has several parts, which one must ship first.
   Each question offers a recommended answer drawn from the prompt and the codebase, so the user
   can accept it quickly.
3. Stop and wait for the answers. This stop is required even when the escalation policy would let
   the agent decide the same points later.
4. Run `speckit-specify` with the prompt and the answers combined as its input.
5. Show the user a short summary of the draft: the user stories with priorities, the out-of-scope
   list, and any `[NEEDS CLARIFICATION]` markers. Continue to Step 3 unless the user objects. The
   four-question limit covers drafting only; clarify-phase escalations in Step 3 are separate.

In both paths, create `run-state.md` in the feature directory (format below) and record which path
was used.

## Step 3. Clarify (the main filtering step)

The installed `speckit-clarify` skill asks the user up to five questions, one at a time. This skill
changes that behavior. Run `speckit-clarify` with this input:

> Autonomous mode. Do not ask the user questions one at a time. For each candidate question: first
> try to answer it from the constitution, the existing codebase, earlier specs in `specs/`, and the
> project docs. If you can answer it, record it in the Clarifications section as
> `- Q: <question> → A: <answer> (auto-resolved: <evidence path or reasoning>)` and apply it to the
> spec. If you cannot, do not ask; return it in a list titled ESCALATE with your recommended answer
> and the reason it needs the user.

If the spec came from the user (Step 2A), add to that input: "Existing requirements are the
user's. Auto-resolved answers may fill gaps and add to the Clarifications section, but must not
change or remove a stated requirement. Any answer that would do so goes to ESCALATE."

Then sort what comes back:

- Auto-resolved items: keep. They stay visible in the spec for review.
- ESCALATE items: check each against the escalation policy. If the policy lets the agent decide,
  choose the recommended answer, record it as `(agent decision: <reason>)`, and apply it. If the
  policy reserves it, add it to the question batch.

If the batch is not empty, ask it (see "Asking the user") and stop the run until the user answers.
Write the answers into the spec's Clarifications section as `- Q: ... → A: ... (user)`.

If the user's answers open new ambiguities, run this step again. Limit: two clarify rounds. After
that, record remaining low-impact items as documented assumptions and move on.

## Step 4. Plan

Run `speckit-plan`. Afterwards, read `plan.md` and handle:

- `NEEDS CLARIFICATION` entries in Technical Context: resolve from the repository (manifests, existing
  stack, constitution) or escalate per policy.
- The Constitution Check section: any violation that the plan justifies in its Complexity Tracking
  table is a reserved decision by default. Escalate it with the plan's justification attached.

Ask any batch and stop, or continue.

## Step 5. Tasks and analyze

1. Run `speckit-tasks`.
2. Run `speckit-analyze`. Sort its findings:
   - **CRITICAL**: fix by re-running the phase that owns the artifact (spec, plan, or tasks) with the
     finding as input. Re-run analyze. If a CRITICAL finding remains after two fix attempts,
     escalate it.
   - **HIGH**: fix if the fix is mechanical (for example a missing task for a stated requirement).
     Otherwise record in `run-state.md` under Deferred findings.
   - **MEDIUM or LOW**: record under Deferred findings. Do not stop.
3. If the policy or constitution requires domain checklists, run `speckit-checklist` for the named
   domains now.

## Step 6. Implement

Before running `speckit-implement`, handle its checklist gate. It stops and asks "Some checklists
have unchecked items. Do you want to proceed?" To avoid that stop:

- `checklists/requirements.md` is maintained by specify and clarify. If items are unchecked, return
  to Step 3 for those items rather than proceeding.
- For custom checklists, unchecked items are reviewer decisions. Escalate them as one batch before
  implementation starts, not during it.

Then run `speckit-implement`. If subagents are available, give each task phase from `tasks.md`
(setup, foundational, each user story, polish) its own subagent.

During implementation:

- A task that fails its tests: retry with a different approach up to three times. Then mark it
  blocked in `run-state.md` with the error and continue with independent tasks.
- A task that turns out to need a decision the spec did not settle: apply the escalation policy.
  If reserved, park that task, add the question to a batch, and keep working on independent tasks.
  Ask the batch when no independent work remains.
- Do not change `spec.md` or `plan.md` silently during implementation. If the design must change,
  record why in `run-state.md` and treat it as an escalation unless the policy allows it.

## Step 7. Converge and finish

1. Run `speckit-converge`. If it appends new tasks, run `speckit-implement` again for those tasks.
   Limit: two converge rounds.
2. Run the project's full test and lint commands.
3. Write the final report (see "Final report"). Do not commit, push, or open a pull request unless
   the policy or the user says to.

## Escalation policy (defaults)

`.specify/memory/run-policy.md` overrides these. The constitution overrides both.

**Reserved for the user. Always escalate:**

- Product intent and scope: what the feature is for, who it serves, what is in or out.
- Anything hard to reverse: data migrations, deleting data, changes to public APIs, file formats,
  or database schemas that other systems use.
- Security and privacy: authentication, authorization, secrets, handling of personal data.
- New external services, paid dependencies, or new licenses.
- Conflicts between the user's stated requirements, or between a requirement and the constitution.
- Constitution violations that the plan wants to justify.
- Unchecked items in custom checklists.

**The agent decides and records the decision:**

- Anything the constitution, existing code, or earlier specs already answer.
- Choices that follow an existing pattern in the codebase (naming, structure, error handling,
  test layout, library already in use).
- Reasonable defaults for unstated non-functional details, recorded as assumptions in the spec
  (for example log levels, pagination sizes, timeouts), unless the constitution sets them.
- Task ordering, internal module structure, and refactoring within the feature's scope.

**When unsure which list applies:** escalate if the choice would take more than about an hour of
work to undo, otherwise decide and record it.

## Asking the user

- One batch per stop. Up to 6 questions. Order them by impact.
- Each question: the decision in one sentence, why it matters, the options, and a recommended
  answer with its reasoning. The user must be able to reply "all recommended".
- Claude Code: use the structured question tool (AskUserQuestion) when available.
- Codex and any other agent: end the turn with a numbered list, and say that replying with numbers and letters is
  enough (for example "1b, 2 recommended, 3: use Postgres").
- Before stopping, write the open questions to `run-state.md`, so the run can resume in a new
  thread.

## run-state.md

Keep this file current at every phase change and every stop.

```markdown
# Run state: <feature name>

Source: <path of the user's spec | prompt>
Phase: <constitution | specify | clarify | plan | tasks | analyze | implement | converge | done>
Status: <running | waiting on user | blocked | done>
Updated: <YYYY-MM-DD HH:MM>

## Open questions
1. ...

## Decisions
- <phase>: <decision> (user | agent: <reason>)

## Blocked tasks
- T0xx: <error summary, attempts made>

## Deferred findings
- <analyze finding id>: <summary>
```

## Final report

End with a short report:

- What was built, the source specification, and the paths of spec, plan, and tasks.
- Test and lint results.
- Decisions the agent made, grouped so the user can review them quickly. Mark any that were close
  calls.
- Blocked tasks and deferred findings, if any.
- Suggested next step (review, commit, pull request).
