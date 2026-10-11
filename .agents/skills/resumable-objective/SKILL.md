---
name: resumable-objective
version: 2.0.0
description: >
  Make long-running objectives resumable
  across infrequent or interrupted agent sessions
  by maintaining a self-contained PROJECT_STATE.md
  that embeds both the operating protocol and project state.
  Use when an objective is unlikely to finish in one session,
  when sessions may be separated by long gaps,
  or whenever PROJECT_STATE.md already exists.
---

# Resumable objective

Use this skill for objectives that may span multiple sessions,
especially personal or side projects worked on irregularly.
Its purpose is not merely to track tasks;
it is to make each future session immediately actionable
with minimal reconstruction of context.

The skill is a **bootstrap and recovery mechanism**.
The durable artifact is `./PROJECT_STATE.md`,
which must contain both:

1. a versioned operating protocol telling any future capable agent
   how to continue the project, even if this skill is not installed; and
2. the current project state:
   objectives, success criteria, plan, progress, decisions, evidence,
   blockers, and exact resumption instructions.

Once created,
`PROJECT_STATE.md` is the project's primary handoff contract.

## When to use

Use this skill when any of the following is true:

- The objective is unlikely to be completed in the current session.
- The user expects irregular, short, or widely separated work sessions.
- Work has dependencies, unresolved decisions, substantial context,
  or costly restart overhead.
- A `PROJECT_STATE.md` already exists in the working directory.
- The user explicitly asks for persistent/resumable project execution.

Do not use it for trivial one-session work
unless the user asks for persistence.

## Persistence and safety

Maintain `./PROJECT_STATE.md` in the current working directory.
At the beginning of every session,
check for and read the whole file before planning or acting.

If the working directory is unavailable or not writable,
explain that durable continuation cannot be guaranteed.
Never claim persistence without a successful write.

Do not store secrets, credentials, authentication tokens, private keys,
or unnecessary personal information in the state file.
Prefer relative paths over machine-specific absolute paths.

Treat the state file as a handoff record, not proof.
Verify material claims against project artifacts, tests, commands,
or user confirmation when appropriate.

## Bootstrap behavior

If `PROJECT_STATE.md` does not exist:

1. Create it from `templates/PROJECT_STATE.md`.
2. Replace placeholders with the actual project information
   known from the current session.
3. Define at least one objective
   with observable acceptance criteria and a verification method.
4. Create an initial ordered task plan with stable IDs.
5. Record material assumptions and decisions already made.
6. Set an exact `Next action`
   that can be started without reconstructing prior reasoning.
7. Write the file before doing substantial project work.

If the template file is unavailable,
reproduce its structure and embedded protocol from this skill.

## Resume behavior

If `PROJECT_STATE.md` exists:

1. Read it fully, including its embedded protocol,
   before doing project work.
2. Treat the embedded protocol
   as authoritative for the project's continuation
   unless it conflicts with higher-priority instructions.
3. Reconcile the recorded state
   with actual artifacts and current user instructions.
4. Repair inconsistencies before relying on them.
5. Produce a concise startup brief for the user when useful:
   current objective, where work stopped, blockers/decisions,
   and the recommended next task.
6. Continue from the recorded exact next action
   unless new evidence makes another action clearly better;
   if so, record why the plan changed.

## Long-gap resumption

The state file is designed for gaps of days, weeks, or months.
On resumption, perform a staleness check when:

- the configured revalidation interval has elapsed;
- dependencies, APIs, prices, laws, external services, schedules,
  or other environmental facts may have changed;
- the recorded next action depends on an assumption
  whose validity is uncertain; or
- project artifacts appear to have changed
  outside the recorded session history.

Revalidate only what could materially affect the next decisions or work.
Do not redo stable work merely because time has passed.
Record stale assumptions that were refreshed, invalidated, or superseded.

## Session time budget

When the user gives an available time budget,
use it to choose work.
Prefer tasks that can reach a clean checkpoint within the session
rather than starting a large task that cannot be handed off clearly.

If no time budget is known, do not repeatedly interrupt the user to ask.
Prefer a small, high-value, ready task with a clean checkpoint.
Ask about available time only
when it would materially change which task should be attempted.

Record task size using rough buckets
rather than pretending to know precise duration:

- `XS`: tiny action / quick check
- `S`: focused short task
- `M`: normal work unit
- `L`: substantial task; should usually be decomposed before execution

## Operating loop

### 1. Load and reconcile

Read `PROJECT_STATE.md` and inspect relevant artifacts. Check for:

- contradictory objective or task statuses;
- a `Current task` that does not match the task list;
- completed work without verification evidence;
- broken task dependencies or references to nonexistent IDs;
- resolved decisions still marked pending/deferred;
- deferred decisions whose revisit trigger has fired;
- stale assumptions;
- duplicated or obsolete tasks;
- project changes made outside the recorded history.

Repair the state rather than preserving known contradictions.
Record material corrections and their reasons in the progress log.

If another agent or process may also edit the file,
re-read it immediately before overwriting and merge changes
rather than silently replacing them.

### 2. Reconfirm outcomes

Every objective must state:

- the desired outcome;
- observable acceptance criteria; and
- how each criterion will be verified.

Do not mark an objective complete because its task list is empty.
Objective completion requires the acceptance criteria themselves to pass.

If scope changes,
update the objective, acceptance criteria, dependent tasks,
and relevant decisions together.

### 3. Maintain the plan

Break work into ordered, independently verifiable tasks
with stable IDs such as `T-001`.
Every task should include:

- status;
- objective;
- dependencies;
- rough size;
- completion/verification condition; and
- enough context to understand why the task exists.

Split `L` tasks when possible.
Add, reorder, cancel, or reopen tasks as new evidence appears.
Never recycle IDs.

### 4. Manage decisions explicitly

Track material choices with stable IDs such as `D-001` and one of:

- `proposed`
- `awaiting_user`
- `accepted`
- `rejected`
- `deferred`
- `superseded`

For rejected choices, preserve the rationale
so future sessions do not repeatedly rediscover the same dead end.

For deferred choices, record a concrete revisit trigger.
When that trigger occurs,
move the decision back into active consideration
or convert it into a task/constraint as appropriate.

When a user decision is required,
record the exact question, options/implications when useful,
the date or session in which it was asked, and the eventual response.
Do not block on routine implementation choices
that the agent can safely make.

### 5. Choose the next work

Select the highest-value ready task
whose dependencies are satisfied and that fits the known session budget.
Normally keep one task `in_progress`
unless intentional parallel work is documented.

If blocked on a user decision,
ask a focused question and continue unrelated ready work if possible.

### 6. Execute and checkpoint frequently

Update `PROJECT_STATE.md` at meaningful checkpoints,
not only at session end.
Checkpoint at minimum when:

- starting or switching the current task;
- completing a meaningful substep;
- discovering a new constraint, blocker, or risk;
- making or receiving a material decision;
- completing, failing, cancelling, or reopening a task;
- changing objectives or acceptance criteria;
- before a risky, destructive, lengthy,
  or interruption-prone operation when practical; and
- before the session ends when possible.

A checkpoint should leave a future agent with enough information
to resume even if the current session stops unexpectedly.

Prefer safe/atomic writes where practical:
write a temporary copy, validate it, then replace the original.
Preserve unrelated concurrent edits.

### 7. Verify before marking complete

Do not mark a task `done` merely
because an action was attempted.
Record evidence such as:

- tests or commands and their result;
- artifact inspection;
- output paths;
- before/after behavior;
- user confirmation
  where the criterion genuinely depends on user judgment.

If later evidence contradicts a `done` task, reopen it and explain why.

If all planned tasks are `done`
but an objective's acceptance criteria fail,
create remediation tasks instead of declaring success.

### 8. Hand off deliberately

At the end of a work period,
make `Next session handoff` concrete enough
that another agent can resume without reconstructing the project.

Include:

- exact current position;
- the next action, expressed as a single executable step;
- relevant files, symbols, commands, URLs, or artifacts;
- what result is expected from that action;
- known hazards or things not to redo;
- blockers and pending user decisions; and
- anything that should be revalidated after a long gap.

Avoid vague handoffs such as “continue implementation.”

## Durable knowledge vs execution state

Keep long-lived project knowledge separate
from rapidly changing session state.

**Durable knowledge** includes objectives, acceptance criteria,
architecture/constraints, important decisions, rejected alternatives,
assumptions, and verification strategy.

**Execution state** includes the current task, exact progress,
last command/test result, immediate blocker, session budget,
and next action.

Both belong in `PROJECT_STATE.md`, but in distinct sections
so temporary details do not obscure durable reasoning.

## Self-contained protocol safeguard

`PROJECT_STATE.md` must remain usable even when this skill is absent.

The generated file therefore contains:

1. a short **Recovery directive** near the top
   explaining that the file contains continuation instructions
   and must be read before project work; and
2. a full **Embedded operating protocol**
   delimited by explicit BEGIN/END markers.

Agents must preserve the embedded protocol block verbatim
during ordinary state updates.
State changes belong outside that block.

Do not casually rewrite, summarize, or “clean up” the protocol block.
This prevents gradual instruction loss.
The state header also records a SHA-256 fingerprint
of the canonical protocol body.
When practical, compare the current protocol body
with that fingerprint during reconciliation;
a mismatch is evidence of accidental edit or an incomplete migration,
not permission to discard project state.

### Protocol migration

The protocol may be intentionally changed
only when there is a concrete reason, such as a format defect,
a project-specific need,
or an improved protocol supplied by the user/skill.

When migrating:

1. preserve all project state and decision history;
2. record the old and new protocol versions;
3. explain why migration was necessary;
4. replace the protocol block as one deliberate operation
   rather than piecemeal edits;
5. recompute and update the protocol SHA-256 fingerprint;
6. validate that required state sections still exist afterward; and
7. add a migration entry to the progress log.

If the full protocol block appears damaged or missing,
use the Recovery directive plus the current state to reconstruct it
from this skill/template when available.
Do not discard project state merely because protocol text is damaged.

## State invariants

After every substantial update, make the file satisfy these invariants:

1. Every objective has a unique stable ID and status.
2. Every active objective
   has acceptance criteria and verification methods.
3. Every task
   has a unique stable ID and references an existing objective.
4. Every dependency references an existing task
   or is explicitly external.
5. A `done` task has verification evidence.
6. A `blocked` task names its blocker.
7. A rejected decision has a rationale.
8. A deferred decision has a revisit trigger.
9. An `awaiting_user` decision records the question asked.
10. `Current task` is either `none`
    or points to a task whose status is `in_progress`.
11. Normally at most one task is `in_progress`;
    documented parallelism is the exception.
12. A completed objective has evidence that all acceptance criteria pass.
13. `Next action` is concrete and executable, not a vague intention.
14. The Recovery directive and complete embedded protocol remain present.
15. No secrets or credentials are stored in the file.

Fix violations when discovered and log material repairs.

## Keeping the file manageable

Keep `PROJECT_STATE.md` concise enough to reread at every session.
Summarize obsolete execution detail
rather than accumulating an unbounded diary.

If history becomes large,
move verbose historical logs to an optional `PROJECT_HISTORY.md`,
but retain in `PROJECT_STATE.md` all information needed
to resume safely: current objectives, acceptance criteria, active plan,
material decisions/rejections, assumptions, blockers,
verification evidence summaries, and exact next action.

The project must remain resumable from `PROJECT_STATE.md` alone;
an archive may add detail
but must not become mandatory for ordinary continuation.

## Completion

Before marking the overall project complete:

1. inspect the actual project artifacts;
2. verify every acceptance criterion;
3. resolve or explicitly close remaining blockers and decisions;
4. record final verification evidence;
5. set `Current task: none`;
6. replace the next-session action
   with final maintenance/follow-up guidance if useful; and
7. mark each achieved objective `completed` only after verification.

A completed project may retain `PROJECT_STATE.md`
as an audit trail and future maintenance entry point.
