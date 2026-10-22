---
name: resumable-objective
description: >
  Keep long-running work resumable across infrequent or interrupted sessions
  by tracking objectives, tasks and decisions in OBJECTIVES.md
  on a meta/BRANCH/objectives branch that runs parallel to a code branch
  and merges it in as work completes.
  Use when an objective is unlikely to finish in one session,
  when sessions may be separated by long gaps,
  or whenever OBJECTIVES.md or a meta/BRANCH/objectives branch
  is in the project or mentioned in the conversation.
metadata:
  version: 3.2.0
---

# Resumable objective

Use this skill for work that spans several sessions,
especially projects worked on irregularly.
The aim is that any later session,
by any capable agent or person,
can start useful work after reading one file,
without reconstructing earlier reasoning.

The durable record is `OBJECTIVES.md`.
It holds the objectives and how each is verified,
the tasks under them,
the decisions they depend on,
and where work stands now.
In a git repository it lives only on objectives branches,
one per code branch,
next to the code but never inside it.

## When to use

Use this skill when any of the following is true:

- The objective is unlikely to be completed in the current session.
- Sessions are expected to be short, irregular or far apart.
- The work has dependencies, open decisions,
  or context that would be costly to rediscover.
- `OBJECTIVES.md` or a `meta/<branch>/objectives` branch already exists.
- The user asks for persistent or resumable tracking.

Do not use it for trivial one-session work
unless the user asks for it.

## Where the file lives

### Git repositories

Each code branch with objectives of its own
has an objectives branch named `meta/<branch>/objectives`,
for example `meta/dev/objectives` for `dev`.
`OBJECTIVES.md` sits at its root, and only there.

- **One objectives branch per code branch.**
  Different code branches have different goals or progress,
  so each keeps its own `OBJECTIVES.md`.
  The branch name says which code branch it follows,
  so the file does not repeat it.
  An objectives branch merges in only its own code branch.
- **Code branches never contain it.**
  Code commits never add or change `OBJECTIVES.md`.
- **The branch runs parallel to the code.**
  `meta/<branch>/objectives` starts from its code branch
  and merges it in as work completes.
  It is never merged back into a code branch,
  and `OBJECTIVES.md` is never cherry-picked into one.
- **The `meta/` prefix** marks the branch as about the project,
  not part of it.
  Other branches of this kind,
  such as `meta/<branch>/time-tracking`,
  belong in the same namespace.

Keep a separate worktree for each objectives branch,
so that the code checkout never has to switch branches:

```sh
git worktree add ../<repository>.objectives/<branch> meta/<branch>/objectives
```

Read the file without a worktree with
`git show meta/<branch>/objectives:OBJECTIVES.md`.

When a new code branch starts from one that has objectives,
give it its own objectives branch only if it has goals of its own.
Refer to the parent's entries by branch and ID,
for example `meta/dev/objectives O-008`,
since IDs are unique only within one file.

### Other directories

Without git, keep `OBJECTIVES.md` in the working directory
and skip the branch rules.
If the location is not writable,
say that progress cannot be kept between sessions.
Never claim persistence without a successful write.

## Recording changes

Every change to `OBJECTIVES.md` is a commit on its objectives branch,
so its history is the project's history.
Each commit describes the change to objectives, tasks or decisions,
not the code.

### Merge code with the update it completes

When code on the code branch completes a task,
completes an objective, or changes a decision,
merge the code branch into its objectives branch
**up to the commit that completes it**,
and stage the `OBJECTIVES.md` update into that merge commit:

```sh
git -C ../<repository>.objectives/<branch> merge --no-ff --no-commit <completing-commit>
# Edit OBJECTIVES.md to record the change.
git -C ../<repository>.objectives/<branch> add OBJECTIVES.md
git -C ../<repository>.objectives/<branch> commit -m "Record T-053 done for O-008."
```

- **Message:** only the description of the change,
  for example `Record T-053 done for O-008.`
  or `Accept D-027: show PDF errors next to their section.`
  Leave out the default "Merge branch ..." line.
- **Granularity:** prefer several small merges to one large one.
  Split at each task completion, objective completion or decision change.
  When several tasks were finished before being recorded,
  make one merge per task, each at the commit that completed it,
  in order.
  Then every merge's code side matches what its update claims.
- **Merges are always clean.**
  Code branches never touch `OBJECTIVES.md`,
  and the objectives branch changes nothing else.
  Each merge differs from the code commit it merges
  only in `OBJECTIVES.md`.
- **Nothing to merge:** if git reports "Already up to date",
  the code is already recorded;
  commit the update on its own (below).
- **Rewritten code history:** if the code branch was rebased or amended
  after being merged, the merge can conflict.
  Resolve it by taking the code side for everything but this file,
  then log the rewrite:

  ```sh
  git restore --source=<completing-commit> --staged --worktree -- . ':!OBJECTIVES.md'
  ```

### Commit updates without code

Use an ordinary commit on the objectives branch,
changing only `OBJECTIVES.md`, for updates without new code:
a new objective, a decision asked or answered,
a checkpoint in the middle of a task,
or a handoff at the end of a session.

### Find what has not been recorded

```sh
git log --oneline meta/<branch>/objectives..<branch>
```

This lists code commits not yet merged into the objectives branch,
which is work the file may not describe yet.
Check it at the start of every session.

### Publishing

Push objectives branches only when the user asks.
Unpublished commits on an objectives branch may be rewritten
to improve them.
Published ones may not.

## Session loop

### 1. Load and reconcile

1. Find the file:
   check `git worktree list` for the objectives worktree,
   and add it with the command above if it is missing,
   for example on a new machine.
2. Read the whole of `OBJECTIVES.md` before planning or acting.
3. Compare it with the project:
   unrecorded code commits (see above), the working tree,
   test results, and current user instructions.
4. Repair contradictions before relying on the file:
   statuses that disagree, done tasks without evidence,
   references to IDs that do not exist,
   decisions still open that were answered,
   deferred decisions whose trigger has fired.
   Log material repairs.
5. If the revalidation interval has passed,
   or the next action depends on something that may have changed
   (dependencies, services, external facts),
   recheck only what could change the next work.
   Do not redo stable work because time has passed.
6. When useful, brief the user:
   current objective, where work stopped,
   open decisions or blockers, and the recommended next task.

### 2. Choose work

Pick the most valuable ready task:
dependencies met, no open decision blocking it,
and small enough to reach a clean checkpoint in the session.
If the user gives a time budget, use it to choose;
otherwise do not ask unless it would change the choice.
Normally keep one task `in_progress`.
Record intentional parallel work.

### 3. Ask decisions well

Make routine implementation choices without asking.
For choices that belong to the user:

- Ask one decision at a time, in plain text,
  with a recommendation first and the main alternatives.
- Record it as `awaiting_user` with the question and the date asked.
- Continue with unrelated ready work while waiting.
- Record the answer in the user's own words, with the date.

### 4. Work and checkpoint

Update the file at meaningful points, not only at the end:
starting or switching a task,
finishing a meaningful step,
finding a blocker, constraint or risk,
making or receiving a decision,
completing, failing, cancelling or reopening a task,
changing an objective,
and before risky, long or interruption-prone work.
A checkpoint should let someone resume
even if the session stops without warning.

If someone else may edit the file,
re-read it just before writing and merge their changes.

### 5. Verify before marking done

A task is `done` only with evidence:
commands and results, tests, inspected output,
commits, or user confirmation
where the criterion depends on the user's judgement.
Say where the evidence came from,
for example a sandbox without a required service,
and what was not verified.

An objective is `completed` only when its acceptance criteria pass.
An empty task list is not enough.
If all tasks are done but a criterion fails,
add tasks to fix it.
If later evidence contradicts a `done` task,
reopen it and say why.

### 6. Hand off

Before the session ends,
make `Status` concrete enough to start the next session immediately:
the exact position,
one executable next action with its expected result,
relevant paths, commands or symbols,
open decisions and blockers,
what not to redo,
and what to recheck after a long gap.
Avoid handoffs such as `continue implementation`.

## OBJECTIVES.md

### Layout

Use these sections in this order.
Leave a section out only if it would be empty.

```markdown
# Objectives: <project name>

Updated: <YYYY-MM-DD>. Recheck assumptions after: <N> days.

## How to maintain this file

<The rules block below, with <branch> filled in.>

## Status

- Current task: <T-xxx or none>
- Progress: <exact position>
- Last verified: <date, environment, result>
- Blockers: <none or what blocks>
- Waiting on the user: <D-xxx, ... or none>

### Next action

<One executable step, its inputs and its expected result.>

### Handoff

- Do not redo: <...>
- Recheck after a long gap: <A-xxx, ...>

## Objectives

## Tasks

## Decisions

## Constraints and assumptions

## Rejected approaches

## Artifacts

## Log
```

`Status` comes first because it is what every session needs first.
The sections after it hold longer-lived knowledge.

### Rules block

Copy this block into `How to maintain this file`,
replacing `<branch>` with the name of the code branch.
It keeps the file usable when this skill is not available.
Change it only to follow a new version of this skill,
and log that change.

```markdown
This file tracks objectives, tasks and decisions
so that work can resume in a later session.
It follows the resumable-objective skill, version 3.2.0.

- Read the whole file before working.
  Start from `Status` and `Next action`.
- This file exists only on branch `meta/<branch>/objectives`,
  and tracks the code branch `<branch>`.
  Code branches never contain it,
  and this branch is never merged into them.
- Run `git log --oneline meta/<branch>/objectives..<branch>`
  to find code commits this file does not describe yet.
- When code completes a task or objective, or changes a decision,
  merge the code branch up to the completing commit,
  and stage the update to this file into that merge.
  The message describes only the update,
  such as "Record T-053 done for O-008."
  Other updates are ordinary commits that change only this file.
- IDs (O-, AC-, T-, D-, A-) are permanent.
  Never reuse them.
- A task is done only with evidence.
  An objective is completed only when its acceptance criteria pass.
- Record user decisions in their words, with the date.
- Never store secrets, credentials or tokens.
  Prefer relative paths.
```

### Entries

Every entry has a permanent ID and a status in backticks.
Use the fields below.
Leave out fields that do not apply,
rather than filling them with "n/a".

**Objectives** state an outcome
with observable acceptance criteria and how each is checked.

```markdown
- **O-008** `[active]` PDF code has a single entry point
  that returns the PDF path
  or the errors explaining why there is none.
  - AC-020: One public function takes one request object.
    Check: review; no use of the builder outside the package.
  - AC-021: Validation reports every problem at once.
    Check: `pytest tests/test_loadsheet`.
  - Evidence: none yet.
  - Notes: Resolves D-022.
```

Statuses: `proposed`, `active`, `paused`, `long-term` (not scheduled),
`completed`, `cancelled` (with the reason).
If scope changes,
update the objective, its criteria, dependent tasks and decisions together.

**Tasks** are ordered, independently checkable steps toward an objective.

```markdown
- **T-053** `[done]` Add the entry point;
  remove partial files on failure.
  - Objective: O-008. Depends on: T-052. Size: M.
  - Done when: tests generate a PDF,
    and return errors without leaving a file.
  - Evidence: 2026-10-16, sandbox without G2:
    `pytest tests/test_loadsheet` 31 passed.
    Code: `ae1950b`.
```

Statuses: `todo`, `in_progress`, `blocked` (name the blocker),
`done` (with evidence), `cancelled` (with the reason).
Sizes: `XS` (quick check), `S` (focused), `M` (normal),
`L` (split it before starting).
Add, reorder, cancel or reopen tasks as evidence changes.
Dependencies point to existing tasks or name something outside the project.

**Decisions** record material choices,
including the ones rejected,
so that later sessions do not rediscover dead ends.

```markdown
- **D-027** `[accepted]` Show PDF errors
  in the existing error output of each section.
  - Context: the PDF callback has two outputs;
    other sections have their own.
  - Decision: user, 2026-10-16:
    "Route them to the existing error outputs."
    Rejected: one list by the Generate button.
  - Revisit when: Dash is upgraded.
```

Statuses: `proposed`, `awaiting_user` (with the question and the date asked),
`accepted`, `rejected` (with the reason),
`deferred` (with a revisit trigger),
`superseded` (naming the decision that replaces it).
When a deferred decision's trigger fires,
reopen it or turn it into a task or constraint.

**Constraints and assumptions:**
constraints are rules the work must follow.
Assumptions (`A-xxx`) are beliefs the plan depends on.
Each says why it matters, how to check it, and when it was last checked.

**Rejected approaches** lists what not to try again, and why,
including approaches dropped without a formal decision.

**Artifacts** maps the main files, commands and external resources
to the objectives that use them.

**Log** has one line per material change, newest last:

```markdown
- 2026-10-18: O-008: T-053 done;
  single entry point `segwiseweb.loadsheet.generate`.
  Code: up to `ae1950b`.
```

### Invariants

After every substantial update:

1. Every ID is unique and has a status.
2. Every active objective has acceptance criteria, each with a check.
3. Every task names an existing objective.
4. Every dependency names an existing task or an external item.
5. Every `done` task and `completed` objective has evidence.
6. Every `blocked` task names its blocker.
7. Every `rejected` decision has a reason,
   every `deferred` one a revisit trigger,
   and every `awaiting_user` one its question.
8. `Current task` is `none` or a task that is `in_progress`.
9. `Next action` is one concrete, executable step.
10. The rules block is present and unchanged apart from the branch name.
11. No secrets or credentials appear.

Fix violations when found and log material repairs.

### Keeping it short

The file is read at the start of every session, so keep it short.
Git keeps every earlier version:
`git log -p meta/<branch>/objectives -- OBJECTIVES.md`
shows the full history.
So when an objective is completed or cancelled,
shorten its tasks to a summary with a pointer to the commits,
and trim old log lines to what a reader still needs.
Keep everything needed to resume:
open objectives and their criteria, the active plan,
decisions and rejections that still apply,
assumptions, blockers, evidence summaries and the next action.

## Starting

When neither the file nor the branch exists:

1. Agree the objective with the user,
   with observable acceptance criteria and how to check each.
2. Create the objectives branch from the code branch,
   and a worktree for it:
   `git branch meta/<branch>/objectives <branch>`,
   then
   `git worktree add ../<repository>.objectives/<branch> meta/<branch>/objectives`.
3. Write `OBJECTIVES.md` with the layout above:
   the rules block, at least one objective,
   an ordered first plan with task IDs,
   known decisions and assumptions,
   and an exact next action.
4. Commit it, for example `Add O-001: <outcome>.`,
   before doing substantial project work.

To convert a state file from an older version of this skill,
such as `PROJECT_STATE.md`,
keep its objectives, tasks, decisions, assumptions,
evidence and log with their IDs,
move them into the layout above,
and drop the old embedded protocol.
When the file follows an older version of this skill,
replace its rules block with the one above and log the change.

## Finishing

Before marking the work complete:

1. Check the actual artifacts and every acceptance criterion.
2. Resolve or explicitly close remaining blockers and decisions.
3. Record the final evidence and mark the objectives `completed`.
4. Set `Current task: none`,
   and replace `Next action` with follow-up or maintenance guidance,
   if any.
5. Record it in a merge of the code branch up to the final commit.

A finished objectives branch stays as the audit trail
and the starting point for later maintenance.
