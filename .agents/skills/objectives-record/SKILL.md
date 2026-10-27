---
name: objectives-record
description: >
  Keep long-running work resumable across infrequent or interrupted sessions
  by tracking objectives, tasks and decisions in an objectives directory:
  a short OBJECTIVES.md index read every session,
  and detail files loaded only when needed.
  In git it lives on a meta/BRANCH/objectives branch
  that runs parallel to a code branch and merges it in as work completes,
  checked out at .meta/objectives/BRANCH inside the code checkout.
  Use when an objective is unlikely to finish in one session,
  when sessions may be separated by long gaps,
  or whenever OBJECTIVES.md, a .meta/objectives or .objectives directory
  or a meta/BRANCH/objectives branch
  is in the project or mentioned in the conversation.
  Formerly named resumable-objective.
metadata:
  version: 5.0.0
---

# Objectives record

Use this skill for work that spans several sessions,
especially projects worked on irregularly.
The aim is that any later session,
by any capable agent or person,
can start useful work after reading one short file,
without reconstructing earlier reasoning.

The durable record is an objectives directory.
Its index, `OBJECTIVES.md`, holds what every session needs:
where work stands, the open objectives and how each is verified,
the open tasks, and the decisions and constraints that still apply.
Detail files hold the rest:
finished objectives with their tasks and evidence,
long decision records, and older log lines.
Like skills, they are listed in the index with a one-line summary
and read only when the work at hand needs them.
Nothing is deleted from the record, so its history does not depend on git.

## When to use

Use this skill when any of the following is true:

- The objective is unlikely to be completed in the current session.
- Sessions are expected to be short, irregular or far apart.
- The work has dependencies, open decisions,
  or context that would be costly to rediscover.
- `OBJECTIVES.md`, a `.meta/objectives` or `.objectives` directory
  or a `meta/<branch>/objectives` branch already exists.
- The user asks for persistent or resumable tracking.

Do not use it for trivial one-session work
unless the user asks for it.

## The objectives directory

```text
objectives/
  OBJECTIVES.md      Index: always read in full.
  details/O-002.md   A finished objective, with its tasks and evidence.
  details/D-012.md   A decision whose record is too long for the index.
  log/2026-10.md     Log lines of one month.
```

- **`OBJECTIVES.md`** is the index.
  Keep it short enough to read at the start of every session:
  aim for under about 500 lines.
- **`details/<ID>.md`** holds one objective or one decision
  in full.
  A decision that still applies can have a detail file too,
  with a summary of it in the index.
  An objective's file can exist while the objective is active,
  holding its finished tasks.
- **`log/<YYYY-MM>.md`** holds the log lines of one month.

Every detail file starts with a header
that says what it holds without reading further,
with the same keys in every file,
so that one search covers all of them:

```markdown
---
id: D-012
status: accepted
summary: Flip when the bubbles stop rising, not on a timer.
applies: src/flipbot/flip/, flip timing
decided: 2026-10-26, user
revisit: A new batter recipe stops making bubbles.
supersedes: D-004
related: O-008, T-053, A-006
---
```

- `id`, `status`, `summary`: always.
- `applies`: the paths, modules or topics the entry constrains
  or delivered, so that an agent can tell whether its work touches them.
- `related`: other IDs.
- Decisions: `decided` (date and who), `revisit` (the trigger),
  `supersedes` or `superseded_by`.
- Objectives: `completed` or `cancelled` (the date).

Leave out keys that do not apply.
Keep each key and its value on one line, never wrapped or folded,
whatever the line length limit for prose,
so that a line-based search sees the whole value.
Keep values short instead:
a `summary` of one sentence,
an `applies` naming directories or topics rather than every file.
Find entries that cover a path without reading them, for example
`grep -l '^applies:.*flipbot/flip' details/*.md`.

The body uses fixed headings, leaving out any that would be empty.
A decision file:

```markdown
## Context
What forced the choice; constraints in play.

## Options
### 1. Watch for bubbles (chosen)
- Pro: works for thin and thick batter. Con: needs the camera (A-006).
### 2. Flip after a fixed 90 seconds (D-004)
- Rejected: thin batter burns, thick batter stays raw.

## Decision
User, 2026-10-26: "Trust the bubbles."

## Consequences
What this commits the code to; open risks.

## Evidence
Spikes, measurements, commands and results.
```

An objective file has `## Delivered`
(what, where by paths and commits, what was left out or not verified),
`## Acceptance criteria`, `## Tasks`, `## Evidence` and `## Notes`.

The index names every detail file with its ID, status and summary,
so a session can tell which ones it needs.

### Where it lives in git

Each code branch with objectives of its own
has an objectives branch named `meta/<branch>/objectives`,
for example `meta/dev/objectives` for `dev`.
The objectives directory is `objectives/` at its root, and only there.

- **One objectives branch per code branch.**
  Different code branches have different goals or progress,
  so each keeps its own record.
  The branch name says which code branch it follows,
  so the record does not repeat it.
  An objectives branch merges in only its own code branch.
- **Code branches never contain it.**
  Code commits never add or change anything under `objectives/`.
- **The branch runs parallel to the code.**
  `meta/<branch>/objectives` starts from its code branch
  and merges it in as work completes.
  It is never merged back into a code branch,
  and nothing under `objectives/` is cherry-picked into one.
- **The `meta/` prefix** marks the branch as about the project,
  not part of it.
  Other branches of this kind,
  such as `meta/<branch>/time-tracking`,
  belong in the same namespace.

Check the objectives branch out at `.meta/objectives/<branch>`
inside the code checkout,
limited to the objectives directory with a sparse checkout,
so that it is within reach of tools that work in the project directory
without holding a second copy of the code:

```sh
exclude="$(git rev-parse --git-common-dir)/info/exclude"
grep -qxF '/.meta/' "$exclude" || echo '/.meta/' >> "$exclude"
git worktree add --no-checkout .meta/objectives/<branch> meta/<branch>/objectives
git -C .meta/objectives/<branch> sparse-checkout set --no-cone '/objectives/'
git -C .meta/objectives/<branch> checkout
```

The index is then `.meta/objectives/<branch>/objectives/OBJECTIVES.md`.

- `.meta/` holds agent state for the project, not only this record,
  such as the instruction backlog.
  Keep the record under `.meta/objectives/` and nothing else there.
- The exclusion goes in `.git/info/exclude`, not `.gitignore`,
  so that no code commit mentions it.
  The command adds it only if it is missing.
- Merges of the code branch still bring in all of its files;
  the sparse checkout only keeps them out of this worktree.
- `git clean -fdx` in the code checkout skips the worktree,
  because it holds its own repository link;
  only `git clean -ffdx` would remove it.
- Tools that skip hidden directories,
  such as pytest's default collection, also skip it.

Read the index without a worktree with
`git show meta/<branch>/objectives:objectives/OBJECTIVES.md`.

When a new code branch starts from one that has objectives,
give it its own objectives branch only if it has goals of its own.
Refer to the parent's entries by branch and ID,
for example `meta/dev/objectives O-008`,
since IDs are unique only within one record.

### Without git

Keep the objectives directory at `.meta/objectives/` in the working directory,
and skip the branch rules.
If the location is not writable,
say that progress cannot be kept between sessions.
Never claim persistence without a successful write.

### Not in temporary directories

Do not keep the record in `/tmp`, a scratchpad or another temporary directory,
even when it is easier to reach.
They are cleared on restart or by cleaners,
and session scratch directories can be wiped between sessions,
so a record there can vanish without warning.
Copies there are fine for scratch work, never as the record.

## Recording changes

In git, every change to the record is a commit on its objectives branch.
Each commit describes the change to objectives, tasks or decisions,
not the code.
The record itself keeps the history:
git makes it easy to share and to see when things changed,
but nothing should be recoverable only from git.

### Merge code with the update it completes

When code on the code branch completes a task,
completes an objective, or changes a decision,
merge the code branch into its objectives branch
**up to the commit that completes it**,
and stage the record update into that merge commit:

```sh
git -C .meta/objectives/<branch> merge --no-ff --no-commit <completing-commit>
# Update the record under objectives/.
git -C .meta/objectives/<branch> add objectives
git -C .meta/objectives/<branch> commit -m "Record T-053 done for O-008."
```

- **Message:** only the description of the change,
  for example `Record T-053 done for O-008.`
  or `Accept D-027: the first pancake goes to the cook.`
  Leave out the default "Merge branch ..." line.
- **Granularity:** prefer several small merges to one large one.
  Split at each task completion, objective completion or decision change.
  When several tasks were finished before being recorded,
  make one merge per task, each at the commit that completed it,
  in order.
  Then every merge's code side matches what its update claims.
- **Merges are always clean.**
  Code branches never touch `objectives/`,
  and the objectives branch changes nothing else.
  Each merge differs from the code commit it merges
  only under `objectives/`.
- **Nothing to merge:** if git reports "Already up to date",
  the code is already recorded;
  commit the update on its own (below).
- **Rewritten code history:** if the code branch was rebased or amended
  after being merged, the merge can conflict.
  Resolve it by taking the code side for everything but the record,
  then log the rewrite:

  ```sh
  git restore --source=<completing-commit> --staged --worktree -- . ':!objectives'
  ```

### Commit updates without code

Use an ordinary commit on the objectives branch,
changing only files under `objectives/`, for updates without new code:
a new objective, a decision asked or answered,
a checkpoint in the middle of a task,
a handoff at the end of a session,
or moving entries into detail files.

### Find what has not been recorded

```sh
git log --oneline meta/<branch>/objectives..<branch>
```

This lists code commits not yet merged into the objectives branch,
which is work the record may not describe yet.
Check it at the start of every session.

### Publishing

Push objectives branches only when the user asks.
Unpublished commits on an objectives branch may be rewritten
to improve them.
Published ones may not.

## Session loop

### 1. Load and reconcile

1. Find the record:
   in git, check `git worktree list` for `.meta/objectives/<branch>`,
   and add it with the commands above if it is missing,
   for example on a new machine.
2. Read the whole of `OBJECTIVES.md` before planning or acting,
   and again after compaction,
   since a summary can drop the position and the decisions.
   Do not read detail files yet.
3. Compare it with the project:
   unrecorded code commits (see above), the working tree,
   test results, and current user instructions.
4. Repair contradictions before relying on the record:
   statuses that disagree, done tasks without evidence,
   references to IDs that do not exist,
   decisions still open that were answered,
   deferred decisions whose trigger has fired,
   detail files missing from the index or listed but missing.
   Log material repairs.
5. If the revalidation interval has passed,
   or the next action depends on something that may have changed
   (dependencies, services, external facts),
   recheck only what could change the next work.
   Do not redo stable work because time has passed.
6. When useful, brief the user:
   current objective, where work stopped,
   open decisions or blockers, and the recommended next task.

### 2. Load details only when needed

Read a detail file when the work at hand needs what it holds:

- the next task names its ID, or depends on it;
- the work changes something its `Applies` line or `applies:` key names,
  such as code a finished objective delivered;
- a decision summary in the index is not enough to apply it,
  or the work may contradict it;
- the user asks about it;
- reconciling needs its evidence.

Read only the files that apply.
The index summary is enough to know that something exists
and roughly what it decided.

### 3. Choose work

Pick the most valuable ready task:
dependencies met, no open decision blocking it,
and small enough to reach a clean checkpoint in the session.
If the user gives a time budget, use it to choose;
otherwise do not ask unless it would change the choice.
Normally keep one task `in_progress`.
Record intentional parallel work.

### 4. Ask decisions well

Make routine implementation choices without asking.
For choices that belong to the user:

- Ask one decision at a time, in plain text,
  with a recommendation first and the main alternatives.
- Record it as `awaiting_user` with the question and the date asked.
- Continue with unrelated ready work while waiting.
- Record the answer in the user's own words, with the date.

### 5. Work and checkpoint

Update the record at meaningful points, not only at the end:
starting or switching a task,
finishing a meaningful step,
finding a blocker, constraint or risk,
making or receiving a decision,
completing, failing, cancelling or reopening a task,
changing an objective,
and before risky, long or interruption-prone work.
A checkpoint should let someone resume
even if the session stops without warning.

If someone else may edit the record,
re-read it just before writing and merge their changes.

The record holds what applies to the current work.
A correction or lesson that applies beyond it
belongs in the project's `AGENTS.md`,
or in the instruction backlog for skills and the user's `AGENTS.md`,
as the instruction-backlog skill describes.

### 6. Verify before marking done

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
reopen it and say why,
moving it back into the index if it had been moved out.

### 7. Hand off

Before the session ends,
make `Status` concrete enough to start the next session immediately:
the exact position,
one executable next action with its expected result,
relevant paths, commands or symbols,
open decisions and blockers,
what not to redo,
and what to recheck after a long gap.
Avoid handoffs such as `continue implementation`.
Then keep the index short (below).

## OBJECTIVES.md

### Layout

Use these sections in this order.
Leave a section out only if it would be empty.

```markdown
# Objectives: <project name>

Updated: <YYYY-MM-DD>. Recheck assumptions after: <N> days.

## How to maintain this record

<The rules block below, with <branch> filled in.>

## Status

- Current task: <T-xxx or none>
- Position: <where work stands now, in a few lines>
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

## Details

## Log
```

`Status` comes first because it is what every session needs first.
`Position` says where work stands now, not how it got there:
the story belongs in the log and in detail files.
The sections after `Status` hold longer-lived knowledge.

### Rules block

Copy this block into `How to maintain this record`,
replacing `<branch>` with the name of the code branch.
It keeps the record usable when this skill is not available.
Change it only to follow a new version of this skill,
and log that change.

```markdown
This record tracks objectives, tasks and decisions
so that work can resume in a later session.
It follows the objectives-record skill, version 5.0.0.

- Read this whole file before working, and again after compaction.
  Start from `Status` and `Next action`.
- Files under `details/` and `log/` are listed in `Details`
  or named by the decision they hold.
  Read one only when the work needs it.
  Never delete record content: move it into a detail file instead.
- This record exists only under `objectives/`
  on branch `meta/<branch>/objectives`,
  and tracks the code branch `<branch>`.
  Code branches never contain it,
  and this branch is never merged into them.
  It is checked out at `.meta/objectives/<branch>`
  in the code checkout, sparse to `objectives/`.
- Before changing something, check the `Applies` lines,
  and `grep '^applies:' details/*.md`, for entries that cover it.
- Run `git log --oneline meta/<branch>/objectives..<branch>`
  to find code commits this record does not describe yet.
- When code completes a task or objective, or changes a decision,
  merge the code branch up to the completing commit,
  and stage the record update into that merge.
  The message describes only the update,
  such as "Record T-053 done for O-008."
  Other updates are ordinary commits that change only `objectives/`.
- IDs (O-, AC-, T-, D-, C-, A-) are permanent.
  Never reuse them.
- A task is done only with evidence.
  An objective is completed only when its acceptance criteria pass.
- Record user decisions in their words, with the date.
- Never store secrets, credentials or tokens.
  Prefer relative paths.
```

Without git, replace the branch items with
"This record lives in `.meta/objectives/` in the project directory."

### Entries

Every entry has a permanent ID and a status in backticks.
Use the fields below.
Leave out fields that do not apply,
rather than filling them with "n/a".

**Objectives** state an outcome
with observable acceptance criteria and how each is checked.

```markdown
- **O-008** `[active]` The robot cooks a stack of pancakes
  without anyone touching the pan.
  - AC-020: Each pancake is flipped exactly once.
    Check: `pytest tests/test_flip`; flip count in the log.
  - AC-021: No pancake leaves the pan raw in the middle.
    Check: user eats the third pancake.
  - Evidence: none yet.
  - Notes: Resolves D-022.
```

Statuses: `proposed`, `active`, `paused`, `long-term` (not scheduled),
`completed`, `cancelled` (with the reason).
If scope changes,
update the objective, its criteria, dependent tasks and decisions together.

**Tasks** are ordered, independently checkable steps toward an objective.

```markdown
- **T-053** `[done]` Watch the batter through the camera;
  flip when the bubbles stop rising.
  - Objective: O-008. Depends on: T-052. Size: M.
  - Done when: tests on recorded videos flip at the right frame,
    and never flip twice.
  - Evidence: 2026-10-16, sandbox without the camera:
    `pytest tests/test_flip` 31 passed on recorded videos.
    Code: `ae1950b`.
```

Statuses: `todo`, `in_progress`, `blocked` (name the blocker),
`done` (with evidence), `cancelled` (with the reason).
Sizes: `XS` (quick check), `S` (focused), `M` (normal),
`L` (split it before starting).
Add, reorder, cancel or reopen tasks as evidence changes.
Dependencies point to existing tasks or name something outside the project.
Keep progress notes to what the next session needs;
long notes belong in the objective's detail file.

**Decisions** record material choices,
including the ones rejected,
so that later sessions do not rediscover dead ends.

```markdown
- **D-027** `[accepted]` The first pancake of a batch goes to the cook.
  - Applies: `src/flipbot/serve/`, plating order.
  - Context: the first pancake comes out pale while the pan heats up;
    nobody wants it on the plate.
  - Decision: user, 2026-10-16:
    "The cook eats the first one. That's the rule."
    Rejected: throwing it away.
  - Revisit when: the pan gets a preheat step.
```

A decision that still applies
can instead be summarized in the index in at most three lines,
with its full record in `details/D-xxx.md`:
what was decided, its status, what it applies to,
what was rejected, the revisit trigger if any, and the file.
Do this once the full record passes about five lines,
and always for spikes, measurements and alternatives in depth.

```markdown
- **D-027** `[accepted]` The first pancake of a batch goes to the cook.
  Applies: `src/flipbot/serve/`, plating order.
  Rejected: throwing it away. Revisit: preheat step. `details/D-027.md`
```

`Applies` is what lets a session tell,
from the index alone,
whether a decision constrains the work at hand.

Keep in the index, in full,
what a session needs to act without opening the file:
the question and date of an `awaiting_user` decision,
and anything a rule of the record refers to.

Statuses: `proposed`, `awaiting_user` (with the question and the date asked),
`accepted`, `rejected` (with the reason),
`deferred` (with a revisit trigger),
`superseded` (naming the decision that replaces it).
When a deferred decision's trigger fires,
reopen it or turn it into a task or constraint.

**Constraints and assumptions:**
constraints (`C-xxx`) are rules the work must follow.
Assumptions (`A-xxx`) are beliefs the plan depends on.
Each says what it applies to;
an assumption also says why it matters, how to check it,
and when it was last checked.

```markdown
- **C-002** The spatula never leaves the pan while the burner is on.
  Applies: `src/flipbot/flip/`, `spatula.py`. From `AGENTS.md`.
- **A-006** The camera sees the whole pan from above.
  Applies: bubble watching (T-053). Check: `flipbot camera --snapshot`
  shows all four edges. Last checked: 2026-10-26.
```

**Rejected approaches** lists what not to try again, why,
and what it applies to,
including approaches dropped without a formal decision.

```markdown
- Tossing pancakes in the air to flip them: impressive,
  but one in five lands on the floor. Applies: flip motion.
```

**Artifacts** lists commands and external resources
that no entry's `Applies` names,
such as a service, a dashboard, or a script to check the environment.
Files are found through `Applies`, not listed here again.

**Details** lists every other detail file, one line each:
those not named by a summary in `Decisions`.
A completed objective's line says what it applies to:
the paths it delivered.

```markdown
- **O-002** `[completed]` Batter is mixed without lumps.
  Applies: `src/flipbot/mix/`. `details/O-002.md`
- **D-004** `[superseded]` Flip on a fixed timer;
  replaced by D-012. `details/D-004.md`
- Log: `log/2026-10.md` (2026-10-22 to 2026-10-27).
```

**Log** has one line per material change, newest last:

```markdown
- 2026-10-18: O-008: T-053 done;
  flips when the bubbles stop rising, `flipbot.flip.watch_bubbles`.
  Code: up to `ae1950b`.
```

### Invariants

After every substantial update:

1. Every ID is unique and has a status.
2. Every active objective has acceptance criteria, each with a check.
3. Every task names an existing objective.
4. Every dependency names an existing task or an external item.
5. Every `done` task and `completed` objective has evidence,
   in the index or in its detail file.
6. Every `blocked` task names its blocker.
7. Every `rejected` decision has a reason,
   every `deferred` one a revisit trigger,
   and every `awaiting_user` one its question.
8. `Current task` is `none` or a task that is `in_progress`.
9. `Next action` is one concrete, executable step.
10. The rules block is present and unchanged apart from the branch name.
11. Every detail file is listed in `Details`
    or named by its summary in `Decisions`,
    every listed file exists,
    and its header's ID, status, `applies` and `revisit`
    match the index.
12. Every decision that applies, constraint, assumption,
    rejected approach and completed objective says what it applies to.
13. No secrets or credentials appear.

Fix violations when found and log material repairs.

## Keeping the index short

The index is read at the start of every session, so keep it short.
Move entries out of it instead of deleting them,
so the record keeps its own history.
Move them when an objective finishes,
at a handoff, or when the index passes about 500 lines.

- **A completed or cancelled objective**
  moves to `details/O-xxx.md` with its criteria, evidence,
  tasks and progress notes, unchanged,
  under `## Delivered`:
  what was delivered, where (paths, commits),
  and what was left out or not verified.
  The index keeps one line in `Details`, with what it applies to.
  Decisions it settled stay in the index while they still apply.
- **Done tasks of an active objective**
  move to that objective's detail file
  once their notes are no longer needed for the next work.
  The objective's index entry says which tasks are done
  and where they are.
- **A decision that still applies**
  moves to `details/D-xxx.md` once its record passes about five lines.
  The index keeps a summary of one or two lines
  that points to the file (see "Entries").
- **A decision that no longer applies**
  (superseded, or about finished work only)
  moves whole to its detail file,
  or to its objective's file when it only concerned that objective.
- **Log lines** older than the current month
  move to `log/<YYYY-MM>.md`.
  Keep the last few lines in the index if they help the next session.
- **`Status` and `Handoff`** lose items that the next work no longer needs.

Keep in the index everything needed to resume:
open objectives and their criteria, the active plan,
decisions, constraints and rejections that still apply,
assumptions, blockers, recent evidence and the next action.

## Starting

When no record exists:

1. Agree the objective with the user,
   with observable acceptance criteria and how to check each.
2. In git, create the objectives branch from the code branch
   and check it out as described in "Where it lives in git":
   `git branch meta/<branch>/objectives <branch>`,
   then the exclusion, worktree and sparse-checkout commands.
   Without git, create `.meta/objectives/` in the working directory.
3. Write `objectives/OBJECTIVES.md` with the layout above:
   the rules block, at least one objective,
   an ordered first plan with task IDs,
   known decisions and assumptions,
   and an exact next action.
4. Commit it, for example `Add O-001: <outcome>.`,
   before doing substantial project work.

## Converting an older record

From version 4
(checked out at `.objectives/<branch>`):

1. Move the worktree under `.meta/`:

   ```sh
   exclude="$(git rev-parse --git-common-dir)/info/exclude"
   grep -qxF '/.meta/' "$exclude" || echo '/.meta/' >> "$exclude"
   mkdir -p .meta/objectives
   git worktree move .objectives/<branch> .meta/objectives/<branch>
   ```

   When no worktrees are left in `.objectives/`,
   remove the empty directory and the `/.objectives/` exclusion.
2. Replace the rules block with the one above.
3. Move decisions that still apply and take more than about five lines
   into detail files, leaving summaries,
   as in "Keeping the index short".
   Remove their lines from `Details`.
4. Add `Applies` to the entries that need it (invariant 12),
   and the new header keys and body headings to detail files.
   Remove files from `Artifacts` once an `Applies` line names them.
5. Commit, for example `Convert the record to objectives-record 5.0.0.`,
   and log the conversion.

From version 3, named resumable-objective
(`OBJECTIVES.md` at the root of the objectives branch,
checked out at `../<repository>.objectives/<branch>`):

1. On the objectives branch, move the file into the directory:
   `mkdir objectives`, then `git mv OBJECTIVES.md objectives/OBJECTIVES.md`.
2. Move completed and cancelled objectives, finished tasks,
   long decision records and old log lines into detail files,
   as in "Keeping the index short",
   and add the `Details` section.
   Rename the section `How to maintain this file`
   to `How to maintain this record`,
   rename `Progress` in `Status` to `Position`
   and shorten it to the current position.
3. Replace the rules block with the one above.
4. Commit, for example `Convert the record to objectives-record 5.0.0.`,
   and log the conversion.
5. Move the worktree into the code checkout
   and make it sparse:

   ```sh
   exclude="$(git rev-parse --git-common-dir)/info/exclude"
   grep -qxF '/.meta/' "$exclude" || echo '/.meta/' >> "$exclude"
   mkdir -p .meta/objectives
   git worktree move ../<repository>.objectives/<branch> .meta/objectives/<branch>
   git -C .meta/objectives/<branch> sparse-checkout set --no-cone '/objectives/'
   ```

From an older state file, such as `PROJECT_STATE.md`,
keep its objectives, tasks, decisions, assumptions,
evidence and log with their IDs,
arrange them as above,
and drop the old embedded protocol.

## Finishing

Before marking the work complete:

1. Check the actual artifacts and every acceptance criterion.
2. Resolve or explicitly close remaining blockers and decisions.
3. Record the final evidence and mark the objectives `completed`.
4. Move them to detail files as in "Keeping the index short".
5. Set `Current task: none`,
   and replace `Next action` with follow-up or maintenance guidance,
   if any.
6. Record it in a merge of the code branch up to the final commit.

A finished objectives branch stays as the audit trail
and the starting point for later maintenance.
