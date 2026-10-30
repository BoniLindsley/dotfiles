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
  version: 6.0.0
---

# Objectives record

Use this skill for work that spans several sessions,
especially projects worked on irregularly.
The aim is that any later session,
by any capable agent or person,
can start useful work after reading one short file
and the few entries that file points to,
without reconstructing earlier reasoning.

The durable record is an objectives directory,
kept like a small database of plain text files.
Each objective, task, decision, constraint and assumption
is an entry file, which is authoritative.
The index, `OBJECTIVES.md`, holds what every session needs:
where work stands, the next step,
and a list of the open entries that can be rebuilt from their files.
Log files record events, one file per day.
Data files hold what a task needs that is not code,
such as a spike or raw measurements.
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
  list.awk            Lists open entries from their headers.
  entries/O-008.md    One objective: outcome, criteria, ordered tasks.
  entries/T-053.md    One task.
  entries/D-027.md    One decision.
  entries/C-002.md    One constraint.
  entries/A-006.md    One assumption.
  log/2026-10-18.md   Events of one day.
  data/T-053/         Files a task or decision needs that are not code.
```

- **`OBJECTIVES.md`** is the index.
  Only `Status`, `Next action`, `Handoff` and `Artifacts`
  are written by hand;
  `Open entries` is the output of `list.awk`.
  It stays short because finished entries drop out of that list.
- **`entries/<ID>.md`** holds one entry,
  with a header of fixed keys and fixed body headings per type:
  see [entries.md](entries.md).
  Entries are authoritative:
  where the index and an entry disagree, the entry wins,
  and the index is corrected.
- **`list.awk`** is copied from this skill when the record starts,
  so the record does not need the skill to list itself.
- **`log/<YYYY-MM-DD>.md`** holds the events of one day:
  status changes, decisions taken, renames, runs.
  Each line names the full IDs it concerns,
  so `grep -H 'T-053' log/*.md` gives an entry's history.
  Log lines go nowhere else.
- **`data/<ID>/`** holds files that the entry `<ID>` needs
  and that are not part of the code base:
  spikes, scripts to run by hand, raw outputs, measurements.
  The entry names each file, for example in its `## Evidence`.
  Nothing in the code imports or tests them;
  a spike that becomes code is rewritten on the code branch.

Data files are read only when the work needs them.
Keep them small text files, up to about 1 MB;
larger or private data stays outside the record,
and the entry says where it is and how to recreate it.
Redact real data before storing it.
Data no longer needed may be deleted,
with a log line naming the files
and where their results are summarized:
the record's summary is the authority, the data only a backup.

### IDs

- **IDs are unique within the record:**
  `O-`, `T-`, `D-`, `C-`, `A-` for entries,
  and `AC-` for acceptance criteria,
  three digits, never reused.
  A new ID is the highest of its prefix in `entries/` and `log/`, plus one:

  ```sh
  grep -rohwE 'T-[0-9]+' entries log | sort -t- -k2 -n | tail -1
  ```

  Create the file only if none exists,
  for example with `set -o noclobber` in the shell,
  so that a collision fails instead of overwriting.
- **Acceptance criteria have no files**,
  so nothing on disk keeps their IDs unique.
  Define each once, as `- AC-020:` at the start of a line
  in its objective's `## Acceptance criteria`;
  `grep -l '^- AC-020:' entries/O-*.md` finds its objective,
  and invariant 17 catches duplicates.
- **IDs do not name their parent.**
  Tasks and criteria keep their IDs if they move to another objective:
  code comments, commit messages and logs refer to them.
- **One session writes the record at a time.**
  Sequential IDs depend on it.
  If parallel writers become normal,
  give each its own range of numbers.
- **Write IDs in full**, never as ranges such as `T-028 to T-031`,
  so that a search for any of them finds every mention.

### Where it lives

In git, the record is `objectives/` on branch `meta/<branch>/objectives`,
which runs parallel to the code branch `<branch>`
and merges it in as work completes.
It is checked out at `.meta/objectives/<branch>`
inside the code checkout, sparse to `objectives/`,
and `/.meta/` is excluded through `.git/info/exclude`.
Code branches never contain it,
and it is never merged into them.
Read the index without a worktree with
`git show meta/<branch>/objectives:objectives/OBJECTIVES.md`.

Without git, the record is `.meta/objectives/` in the working directory.
Never keep it in a temporary directory.
The reasons, the commands to set it up,
and the rules for new code branches
are in [git-setup.md](git-setup.md).

## Recording changes

In git, every change to the record is a commit on its objectives branch.
Each commit describes the change to objectives, tasks or decisions,
not the code.
The record itself keeps the history,
in its entries and its log:
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
or a handoff at the end of a session.

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
   and add it if it is missing,
   with the commands in [git-setup.md](git-setup.md),
   for example on a new machine.
   A record of an older version may be checked out elsewhere,
   such as `.objectives/<branch>` for version 4:
   use it where it is, following its own rules block,
   and see [lifecycle.md](lifecycle.md) on converting it.
2. Read the whole of `OBJECTIVES.md` before planning or acting,
   and again after compaction,
   since a summary can drop the position and the decisions.
3. Rebuild the open entries
   (`awk -f list.awk entries/*.md | sort | cut -f 2-`)
   and compare them with `Open entries`.
   Where they differ, the entries are right: correct the index.
4. Compare the record with the project:
   unrecorded code commits (see above), the working tree,
   test results, and current user instructions.
5. Repair contradictions before relying on the record,
   checking the invariants below:
   statuses that disagree with evidence,
   references to IDs that do not exist,
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
  `grep -l '^applies:.*<path>' entries/*.md`,
  including finished objectives that delivered that code;
- its summary is not enough to apply it,
  or the work may contradict it;
- the user asks about it;
- reconciling needs its evidence.

Read only the entries that apply.
A summary in `Open entries` is enough to know that something exists
and roughly what it says.
Entries not listed there are finished;
find them with `grep` when the work touches what they cover.

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
  with the question under `## Question` and the date in `asked`.
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
adds a line to today's log for each event,
and, when a task changes status,
updates `Current task`, `Position`, `Next action`
and `Open entries` in the index together.

Put each piece of content where [entries.md](entries.md) says:
state and findings in the entry they describe,
or in the entry that will use them, citing their source;
events in the log;
where work stands in `Status`.

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
reopen it, say why in the entry, and log it.

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

<The rules block from rules-block.md, with <branch> filled in.>

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

## Open entries

<The output of awk -f list.awk entries/*.md | sort | cut -f 2-.>

## Artifacts
```

`Status` comes first because it is what every session needs first.
`Position` says where work stands now, not how it got there:
the story belongs in the log.
`Handoff` holds only what the next work needs;
lasting conventions are constraints.

`Open entries` lists, one line each,
objectives that are `proposed`, `active`, `paused` or `long-term`;
tasks that are `todo`, `in_progress` or `blocked`, with their objective;
decisions that are `proposed`, `awaiting_user`, `accepted` or `deferred`;
constraints that are `active`;
and assumptions that are `unverified` or `holds`:

```markdown
- O-008 `[active]` The robot cooks pancakes without help.
- T-053 `[todo]` O-008: Flip when the bubbles stop rising.
- D-027 `[accepted]` The first pancake of a batch goes to the cook.
- C-002 `[active]` The spatula never leaves the pan while the burner is on.
- A-006 `[holds]` The camera sees the whole pan from above.
```

**Artifacts** lists commands and external resources
that no entry's `applies` names,
such as a service, a dashboard, or a script to check the environment.

### Invariants

After every substantial update:

1. Every entry file's name is its `id`,
   and its `status` is one of its type's values ([entries.md](entries.md)).
2. Every active objective has acceptance criteria, each with a check.
3. Every task names one existing objective in `objective`,
   and appears in that objective's `## Tasks`.
4. Every `depends` names an existing entry or an external item.
5. Every `done` task and `completed` objective has evidence.
6. Every `blocked` task names its blocker.
7. Every `rejected` decision has a reason,
   every `deferred` one a `revisit` trigger,
   every `superseded` one its `superseded_by`,
   and every `awaiting_user` one its question and `asked`.
8. `Current task` is `none` or a task that is `in_progress`,
   and `Next action` belongs to it or to the task that comes next.
9. `Next action` is one concrete, executable step
   that has not been done yet.
10. The rules block is present and unchanged apart from the branch name
    (compare with [rules-block.md](rules-block.md)),
    and `list.awk` matches this skill's.
11. `Open entries` matches the output of `list.awk`.
12. Every objective, decision, constraint and assumption
    says what it applies to.
13. IDs are written in full everywhere, never as ranges.
14. Log lines are only in `log/<YYYY-MM-DD>.md`.
15. Every directory under `data/` belongs to an existing ID,
    every file in it is named by that entry,
    and every named file exists.
16. No secrets or credentials appear.
17. Every acceptance criterion ID is defined once:
    `grep -ohE '^- AC-[0-9]+' entries/O-*.md | sort | uniq -d`
    prints nothing.

Fix violations when found and log material repairs.

## Keeping the index short

Finished entries leave `Open entries` by themselves,
so the index grows only with open work.
Keep the hand-written parts short too:

- **`Status` and `Handoff`** lose items that the next work no longer needs.
- **Notes that outlast the next task** go to the entry they concern.
- **Conventions** go to constraints, or to `AGENTS.md`.
- **An objective with too many open tasks** to read at a glance
  is usually several objectives.

Keep in the index everything needed to resume:
the position, blockers, the next action,
and what not to redo.

## Reference files

Read these only when the work needs them:

- [entries.md](entries.md): header keys, statuses and body headings
  of each entry type, and what content goes where.
- [git-setup.md](git-setup.md): where the record lives in git and why,
  the worktree commands, new code branches, the record without git.
- [rules-block.md](rules-block.md): the rules block every index carries.
- [list.awk](list.awk): the listing script every record carries.
- [lifecycle.md](lifecycle.md): starting a record,
  finishing an objective, converting an older record.
