---
name: objectives-record
description: >
  Keep long-running work resumable across infrequent or interrupted sessions
  by tracking objectives, tasks and decisions in an objectives directory:
  a short OBJECTIVES.md index read every session,
  and one file per objective, task, decision, constraint and assumption,
  read when the work needs it.
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
  version: 6.2.0
---

# Objectives record

Use this skill for work that spans several sessions,
especially projects worked on irregularly.
The aim is that any later session,
by any capable agent or person,
can start useful work after reading one short file
and the few entries that file points to,
without reconstructing earlier reasoning.

The record is a small database of plain text files.
Each objective, task, decision, constraint and assumption
is an entry file, which is authoritative.
The index, `OBJECTIVES.md`, holds where work stands and the next step;
`sh record.sh list` lists the open entries from their files.
Log files record events, one file per day.
Nothing moves when work finishes: an entry's status changes in place.
Nothing but data no longer needed is deleted,
so the record's history does not depend on git.

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
  OBJECTIVES.md       Index: always read in full.
  record.sh           Lists, checks and searches the entries.
  entries/O-008.md    One objective: outcome, criteria, ordered tasks.
  entries/T-053.md    One task.
  entries/D-027.md    One decision.
  entries/C-002.md    One constraint.
  entries/A-006.md    One assumption.
  log/2026-10-18.md   Events of one day, one line each.
  data/T-053/         Files an entry needs that are not code.
```

- **`OBJECTIVES.md`**: `Status`, `Next action`, `Handoff` and `Artifacts`,
  all written by hand; it holds no lists of entries.
  Where the index and an entry disagree, the entry wins.
- **`entries/<ID>.md`**: header keys, statuses, body headings,
  IDs, what goes where, data files and invariants
  are in [entries.md](entries.md).
- **`record.sh`** is copied from this skill when the record starts,
  so the record does not need the skill to maintain itself:
  `list`, `check`, `applies <path>`, `next <prefix>`.
  It relies on the fixed start of every entry:
  `---`, `id:`, `status:`, `summary:`, and for tasks `objective:`.
- **`log/<YYYY-MM-DD>.md`**: events, one physical line each,
  naming the full IDs they concern,
  so `grep -H T-053 log/*.md` gives an entry's history.

In git, the record is `objectives/` on branch `meta/<branch>/objectives`,
checked out at `.meta/objectives/<branch>` inside the code checkout,
sparse to `objectives/`, with `/.meta/` excluded through
`.git/info/exclude`.
Code branches never contain it, and it is never merged into them.
Without git, it is `.meta/objectives/` in the working directory.
Never keep it in a temporary directory.
Setup, commits and merges are in [git-setup.md](git-setup.md).

## Session loop

### 1. Load and reconcile

1. Find the record:
   in git, check `git worktree list` for `.meta/objectives/<branch>`,
   and add it if it is missing ([git-setup.md](git-setup.md)).
   A record of an older version may be checked out elsewhere,
   such as `.objectives/<branch>` for version 4:
   use it where it is, following its own rules block,
   and see [lifecycle.md](lifecycle.md) on converting it.
2. Read the whole of `OBJECTIVES.md` before planning or acting,
   and again after compaction,
   since a summary can drop the position and the decisions.
3. Run `sh record.sh list` for the open entries,
   and `sh record.sh check`.
   Where the index and the entries differ, the entries are right.
4. Compare the record with the project:
   unrecorded code commits
   (`git log --oneline meta/<branch>/objectives..<branch>`),
   the working tree, and current user instructions.
   Rerun tests only when something changed since `Last verified`,
   or the next action depends on them.
5. Repair contradictions before relying on the record:
   statuses that disagree with evidence,
   decisions still open that were answered,
   deferred decisions whose trigger has fired.
   Log material repairs.
6. If the revalidation interval has passed,
   or the next action depends on something that may have changed
   (dependencies, services, external facts),
   recheck only what could change the next work.
   Do not redo stable work because time has passed.
7. When useful, brief the user:
   current objective, where work stopped,
   open decisions or blockers, and the recommended next task.

### 2. Read the entries the work needs

Read an entry when the work at hand needs it:

- `Next action` or the current task names it;
- it is the current task's objective, or a task it depends on;
- its `applies:` covers what the work changes:
  `sh record.sh applies <path>`, for each file or directory,
  including finished objectives that delivered that code;
- its summary is not enough to apply it,
  or the work may contradict it;
- the user asks about it;
- reconciling needs its evidence.

Read only the entries that apply.
A summary from `record.sh list` is enough to know that something exists.
Entries not listed there are finished;
find them with `record.sh applies` or `grep`
when the work touches what they cover.

### 3. Choose work

Pick the most valuable ready task:
dependencies met, no open decision blocking it,
and small enough to reach a clean checkpoint in the session.
Follow the order in its objective's `## Tasks`
unless a reason to change it is recorded.
If the user gives a time budget, use it to choose;
otherwise do not ask unless it would change the choice.
Normally keep one task `in_progress`.
Record intentional parallel work.

### 4. Ask decisions well

Make routine implementation choices without asking.
For choices that belong to the user:

- Ask one decision at a time, in plain text,
  with a recommendation first and the main alternatives.
- Record it as a decision entry, `awaiting_user`,
  with the question under `## Question` and the date in `asked`
  ([entries.md](entries.md) has the rest of its lifecycle).
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

An update changes the entries it concerns,
adds one log line per event,
and, when a task changes status,
updates `Current task`, `Position` and `Next action` together,
then runs `sh record.sh check`.
New IDs come from `sh record.sh next <prefix>`.
Put each piece of content where [entries.md](entries.md) says.

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
Set `completed:` to the date.

An objective is `completed` only when its acceptance criteria pass.
An empty task list is not enough.
If all tasks are done but a criterion fails,
add tasks to fix it.
If later evidence contradicts a `done` task,
reopen it, say why in the entry, and log it.
Finishing an objective is in [lifecycle.md](lifecycle.md).

### 7. Hand off

Before the session ends,
make `Status` concrete enough to start the next session immediately:
the exact position,
one executable next action with its expected result,
open decisions and blockers,
what not to redo,
and what to recheck after a long gap.
Avoid handoffs such as `continue implementation`.
Keep the hand-written parts short:
notes that outlast the next task go to the entry they concern,
and conventions go to constraints or `AGENTS.md`.

## OBJECTIVES.md

```markdown
# Objectives: <project name>

Updated: <YYYY-MM-DD>. Recheck assumptions after: <N> days.

## How to maintain this record

<The rules block from rules-block.md, with <branch> filled in.>

## Status

- Current task: <T-xxx or none>
- Position: <where work stands now, in a few lines>
- Last verified: <date, environment, result>
- Blockers: <none or what blocks>
- Waiting on the user: <D-xxx, reviews or answers owed, or none>

### Next action

<One executable step, its inputs and its expected result,
naming the entries to read first.>

### Handoff

- Do not redo: <...>
- Recheck after a long gap: <A-xxx, ...>

## Artifacts
```

- `Current task` holds only a task ID or `none`;
  what comes next belongs in `Position` and `Next action`.
- `Position` says where work stands now, not how it got there:
  the story belongs in the log.
- `Waiting on the user` names decisions `awaiting_user`,
  and anything else owed by the user, such as a review.
- `sh record.sh list` shows, one line each, entries not finished:
  objectives `proposed`, `active`, `paused` or `long-term`;
  tasks `todo`, `in_progress` or `blocked`, with their objective;
  decisions `proposed`, `awaiting_user`, `accepted` or `deferred`;
  constraints `active`; assumptions `unverified` or `holds`.
- `Artifacts` lists commands and external resources
  that no entry's `applies` names,
  such as a service, a dashboard, or a script to check the environment.

The index stays short by itself: it holds no lists of entries.
An objective with too many open tasks to read at a glance
is usually several objectives.

## Reference files

Read these only when the work needs them:

- [entries.md](entries.md): header keys, statuses and body headings
  of each entry type, IDs, what goes where, data files, invariants.
- [git-setup.md](git-setup.md): where the record lives in git and why,
  the worktree commands, commits and merges, the record without git.
- [rules-block.md](rules-block.md): the rules block every index carries.
- [record.sh](record.sh): the helper every record carries.
- [lifecycle.md](lifecycle.md): starting a record,
  finishing an objective, converting an older record.
