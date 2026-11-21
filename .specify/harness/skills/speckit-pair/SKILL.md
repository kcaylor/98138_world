---
name: speckit-pair
description: Coordinate an explicitly requested Claude-planned, Codex-implemented Spec Kit feature, or resume a feature with handoff.md. Uses T3 delegates and a durable local ledger. Ordinary small fixes remain on the direct path.
---

# Claude planning and Codex implementation

Use only when the user requests pairing, the run policy sets `paired: default` under
`## Agent roles`, or the selected feature already has `handoff.md`. Installing this skill does
not opt a project in. Small self-contained fixes use Codex and the project's ordinary workflow;
use native same-provider delegation where the runtime requires it, or T3 for cross-provider or
worktree tasks. Do not manufacture a specification or paired run for a small fix.

Read the project's constitution and run policy. Existing session authorization applies. Do not
ask again for an action already authorized. Before planning, run `speckit-harness ensure --agent
<key>` and follow its output; do not refresh generated files during an active contract. Paired
workers start by verifying the contract, not by running ensure. If inherited instructions require
a refresh, do it in the coordinator between contracts, then re-pin affected files.

## Prepare the contract

1. Confirm the parent checkout belongs to the intended T3 project. For a new feature, Spec Kit
   specify creates its feature branch; for an existing feature, use its branch. From commit S
   onward, require that local feature branch. The helper refuses main/master and origin's symbolic
   default branch. A missing/template constitution must be resolved through the constitution
   workflow before pin, which otherwise exits 25. Ensure generated
   workflow files are committed so T3 worktrees can see them. Check commit authority before
   planning; no additional approval is needed when session instructions already authorize it.
2. Call `orchestrator_capabilities` once per thread as required by T3. Use the actual available
   provider ids. If a required provider is unavailable, report it and stop; do not choose another.
3. Delegate planning to Claude, `role: "design"`, `isolation: "shared"`, using the existing
   Spec Kit planning phases through analyze, following `speckit-run` phase guidance directly
   without invoking its coordinator routing again. Tell the planner to stop before implementation,
   preserve user scope, and use the project's escalation policy. Give it the feature request and
   all established decisions. Do not ask questions the user already answered.
4. Planner commits spec.md, plan.md, tasks.md and applicable approved policy files as S. Copy
   `.specify/harness/templates/handoff.md` into the feature directory, fill providers, milestones,
   task ids and actual validation commands, then run:

       speckit-harness handoff pin --feature specs/<feature>

   Commit only handoff.md as H. Report full S and H. H is never embedded inside itself. Do not
   edit a committed contract. For a revision, cancel and confirm any active task, cancel the run,
   remove the old handoff in S', then add H' with `supersedes` set to the previous H.
5. Coordinator runs `handoff start --contract <H> --holder <thread-label>`. Capture its epoch.
   All further mutations require this holder and epoch, except takeover. Never infer ownership
   from a process or thread being gone: read the ledger.

## Dispatch protocol

Only the coordinator writes the ledger. Every command below also takes `--feature <feature>`;
mutations except start/takeover take `--holder <label> --epoch <N>`.

- `handoff show --feature <feature> --json` gives `state` and `next`.
- For `dispatch <role>`, run `handoff dispatch-begin --role <role> --provider <contract-provider>`.
  This writes a durable intent and prints `key` and `brief`. Pass the brief unchanged, the pinned
  milestone tasks, validation commands and relevant repository context to the delegate. In the
  fix phase, include the previous reviewer's numbered findings verbatim, with its reviewed commit
  and result link. Give those findings to the next reviewer too, so each can be checked. Recover
  missing findings from the exact review result before dispatching; do not guess from a summary.
- Call T3 exactly once, using the returned key:

  ```json
  {
    "clientRequestId": "<key>",
    "target": {"providerInstanceId": "<contract-provider>"},
    "role": "implementation",
    "isolation": "worktree",
    "mode": "async",
    "title": "<key>: <milestone>",
    "task": "<brief and milestone scope>"
  }
  ```

  Use `role: "review"` for the reviewer, also in a fresh worktree. Do not create a child's
  checkout in shell commands. Omit runtimeMode and interactionMode overrides; inherit settings.
  Honor the tool's `next`: when completion wakes the thread, end the turn without polling.
- Record the returned exact task id with `handoff dispatch-record --key <key> --task-id <id>`
  before ending the turn. Never record an id guessed from a title or thread list.
- For a definite rejected start, use `dispatch-record --key <key> --start-error --class
  quota|rate|auth|unavailable`. If a task might have been created, use timeout or unknown instead.
  An error can be recorded only once. Subsequent recovery uses reconcile, never dispatch-record.
- At completion, read the actual task result and require the PAIR-RESULT block. Record only an
  observed terminal task status after delegated/background work has settled. A completed run
  with pending work is still waiting; do not fail it merely because an interim message lacks
  a result block. Missing/malformed final results become `--status failed --class unknown`
  with the actual observed status. Never convert an interim notification into success.
- Implementer completion: `dispatch-complete --key <key> --observed completed --status ok
  --head <full-SHA> --exit pass|fail`. The helper adopts only a descendant without pinned edits,
  by fast-forward. Never cherry-pick or reset to get past a refusal.
- Reviewer completion: `dispatch-complete --key <key> --observed completed --status ok
  --reviewed-head <full-SHA> --verdict accept|changes|escalate`. Acceptance requires passing exit
  evidence at exactly that head. If tests failed, request changes, not acceptance.
- Failure: `dispatch-complete --key <key> --observed failed|interrupted|completed --status failed
  --class quota|rate|auth|unavailable|unknown|transient`. Only an explicitly transient failure
  consumes a bounded retry. Provider errors stop the run, with no fallback.
- Cancellation: record `cancel-request --key <key>`, call `task_cancel` with the exact id, and
  keep ownership until observed cancelled. Then `dispatch-complete --key <key> --observed
  cancelled --status cancelled`. A cancel request or interrupted status is not cancellation.
- `unblock --user-confirmed --reason <text>` preserves phase and provider. It never replenishes
  exhausted limits. Revise the contract to change providers or raise exhausted limits.
- `takeover --holder <new-label> --reason <text>` increments the epoch. Follow the conditions
  below; holder labels are not authentication. `cancel-run --reason <text>` requires no active task.

Exit 20 means lock timeout, 21 disallowed state/role/epoch, 22 occupied dispatch, 23 drift,
24 exhausted bound, 25 malformed input/corrupt ledger and 26 failed adoption. On 13, ask the
user to resolve ledger access; do not change permissions. Do not manually edit event logs.
The ledger is local to this clone and machine; network filesystems/shared ledgers are unsupported.

## Runtime evidence and unresolved capabilities

Record capabilities from actual tool results, not assumptions. In particular, confirm T3's parent
checkout/commit and shared Git object store before worktree adoption; if they cannot be verified,
stop and report the missing capability. Cross-thread task access, completion delivery after a
restart, and quota error shape are not guaranteed. A readable completion is not guaranteed merely
because a task id is known. Do not claim T3 deduplicates clientRequestId.

Within a paired run, a recorded `changes` verdict moves to fix and normally requires a fresh
implementer dispatch. The coordinator must not edit the parent while the run remains active.
A skill cannot override higher-priority runtime instructions. If the runtime requires the
coordinator to fix small findings directly, first record the review's completion, confirm no
dispatch remains active, and run `cancel-run --reason runtime-direct-fix`. Explain that the paired
run has ended before making the authorized direct fix under the runtime and project rules.
Do not launch a forbidden replacement delegate, silently switch providers, or claim that the
cancelled run finished successfully. To return to pairing afterwards, create S'/H' with supersedes
and start a new run. The same clean exit applies when the user requests a direct fix.

At done, report the commits and validation; landing follows the project's existing authority.
This skill never pushes, releases, or merges to a default branch on its own.

## Authority and precedence

Highest first; the helper's `--help` states the same order.

1. The platform's and agent runtime's safety and permission rules.
2. Kelly's explicit instructions in the session.
3. Kelly's global instructions (`~/AGENTS.md`, `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`).
4. The project's constitution.
5. The project's `.specify/memory/run-policy.md`.
6. The project's AGENTS.md and CLAUDE.md.
7. speckit-pair defaults.

No project file can raise its own rank or grant permissions. The workflow adds **no approvals**:

- it changes no permission, sandbox, runtime-mode, network, account or routing setting
- it adds no mandatory quota or account prompt
- it never reads `~/.t3/service.env`, tokens, or provider configuration files

The coordinator's one capability check is `orchestrator_capabilities`, which T3 already requires
once per thread. It is a tool call, not a question for Kelly. If Kelly wants to confirm account
routing in the T3 settings, that is optional and never gates a run.

**Committing is required.** T3 worktrees are created from the parent's commit, so a paired run
needs commits on a local feature branch. If the project's policy does not allow agents to commit on
a feature branch, the run cannot start. It stops before planning and reports this as a reserved
decision. The workflow never pushes or merges to a default branch. Landing follows the project's
policy, as before.

## Cooperative limits

- **Holder labels are not authenticated.** The helper cannot tell which thread or process is
  calling it. `--holder` is a label for the log. The epoch protects against *mistakes*, such as a
  stale coordinator still running. It does not protect against a malicious caller: anyone who can
  run the helper as Kelly's user can read the epoch and run `takeover`.
- **When takeover is allowed:** by convention, only when the previous coordinator thread has
  finished or been archived, or when Kelly asks. The helper logs every takeover but cannot check
  these conditions.
- **The helper cannot detect whether a checkout is a T3 worktree, a Codex worktree, a hand-made
  worktree, or one a native session is using.** It enforces only what git shows:
  - the parent checkout has no tracked changes
  - the parent is on `feature_branch`
  - the parent HEAD equals the ledger head
  - a reported head descends from it

  Keeping native sessions out of T3 worktrees is a convention. The coordinator always dispatches
  implementers with `isolation: "worktree"`.
- **Values reported in the final block are trusted as reported.** These are task status, worker
  head, exit-command results and verdicts. The helper checks their *shape* and their relation to
  git (ancestry, which paths changed, the head under review). It cannot check whether a worker
  really ran the tests. The reviewer's verdict is the check on that.

## Resolving an uncertain dispatch

The status is `dispatch-uncertain` in two cases: an `intent` was written but no task id was
recorded (a crash between steps), or the start returned `timeout` or `unknown`. In that state:

- No new dispatch is possible.
- The coordinator may resolve it **only** with a task id it has from a tool result. That id comes
  from its own `delegate_task` result, or from reading the previous coordinator thread
  (`t3_thread_read`) and finding the exact `delegate_task` result that carries this key. It runs
  `reconcile --task-id`.
- Matching by title, by thread list, or by guessing is forbidden. So is starting the step in
  another thread.
- Otherwise the coordinator tells Kelly in one line which key and step are uncertain. Kelly checks
  T3 and answers either "task X" or "none". The coordinator runs the matching `reconcile`
  (`--no-task --user-confirmed` for "none").

## Brief and final block

`dispatch-begin` prints a brief header for the coordinator to paste unchanged into the task:

- the contract H, feature, milestone, phase, round and key
- the head to start from
- the command to run first: `speckit-harness handoff verify --contract H`
- the scope limits (no edits to pinned paths or `handoff.md`)
- the required final block

Every worker ends with:

```
PAIR-RESULT key=<K> status=ok|failed class=<…> head=<full SHA> exit=pass|fail
            verdict=accept|changes|escalate reviewed-head=<full SHA> findings=<n>
```

Implementers report `head` and `exit`. Reviewers report `verdict`, `reviewed-head` and a numbered
list of findings. Each finding is tied to a requirement id or a test, and any finding outside the
contract's scope is listed as deferred. If the block is missing or malformed, the coordinator
records `failed --class unknown`, and the status becomes `blocked-provider`. Kelly then decides.

## Resume in any thread

1. `show --json`.
2. If this thread is not the recorded holder: run `takeover` only under the cooperative conditions above.
3. Follow `next`, a deterministic field printed by `show`:
   - `dispatch <role>`
   - `wait <taskId>`
   - `reconcile <key>`
   - `ask-user <reason>`
   - `confirm-cancel <taskId>`
   - `done`
4. For `wait <taskId>` or `confirm-cancel <taskId>` in a thread that did not start the task,
   do not assume completion notifications will reach this thread. Try available read-only T3
   access to the exact task. If it is unreadable or its completion cannot be delivered here,
   ask Kelly in one line, giving the dispatch key and exact task id, to report its terminal T3
   status/result or cancel it in T3. Do not poll a delegated task against the runtime's rules.
   `show` continues to print `wait` or `confirm-cancel`; the helper has no orphan state.
5. Keep the slot until terminal evidence arrives from T3 or Kelly's explicit report of T3's
   status. Then use `dispatch-complete` with that observed status and the result fields. A
   completed status alone is not passing tests or an acceptance verdict: if the final result
   block is unavailable, record failed/unknown, never ok. A reported cancelled status permits
   cancelled completion. A still-running or unknown status permits neither. Nothing is
   re-dispatched and cancel-run cannot bypass the occupied slot.
