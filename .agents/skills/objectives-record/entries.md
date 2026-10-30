# Entry files

Every objective, task, decision, constraint and assumption
is one file, `entries/<ID>.md`.
It starts with a header that says what it holds without reading further.
The first lines are fixed, in this order:
`---`, `id:`, `status:`, `summary:`, and for tasks `objective:`;
`record.sh` reads them by position.
Other keys follow in any order:

```markdown
---
id: T-053
status: todo
summary: Flip when the bubbles stop rising.
objective: O-008
depends: T-052, A-006
size: M
applies: src/flipbot/flip/
---
```

## Header keys

- `id`, `status`, `summary`: always.
  `id` matches the file name.
  `summary` is one sentence; `record.sh list` shows it.
- `objective`: the parent of a task. Exactly one ID.
- `depends`: for a task, the IDs or external items it waits for.
- `size`: for a task, `XS`, `S`, `M` or `L` (split before starting).
- `applies`: the paths, modules or topics the entry constrains
  or delivered, so that an agent can tell whether its work touches them.
  Paths are relative to the repository root;
  a directory ends with `/` and covers everything below it.
  Required for objectives, decisions, constraints and assumptions;
  optional for tasks.
- `related`: other IDs, when no more specific key fits.
- Decisions: `decided` (date and who), `asked` (date, while
  `awaiting_user`), `revisit` (the trigger),
  `supersedes` or `superseded_by`.
- Assumptions: `checked` (date and how it was last checked).
- Constraints: `source` (where the rule comes from, such as `AGENTS.md`).
- Objectives and tasks: `completed` or `cancelled` (the date).

Rules, so that line-based searches find every entry:

- One `key: value` per line, at the start of the line.
  Never wrap or fold a value, whatever the line length limit for prose;
  keep values short instead.
- Lists of IDs are comma-separated, in full: `T-028, T-029`,
  never `T-028 to T-029`.
- `status` takes only the values of the entry's type, below.
- Leave out keys that do not apply.

`grep -l '^objective: O-008$' entries/T-*.md` lists the tasks of O-008.
`sh record.sh applies src/flipbot/flip/watch.py` lists the entries
whose `applies` names that path or a directory above it.

## IDs

- IDs are unique within the record:
  `O-`, `T-`, `D-`, `C-`, `A-` for entries,
  and `AC-` for acceptance criteria,
  three digits, never reused.
  `sh record.sh next T` gives the next one:
  the highest of the prefix in `entries/` and `log/`, plus one.
  Create the file only if none exists,
  for example with `set -o noclobber` in the shell,
  so that a collision fails instead of overwriting.
- Acceptance criteria have no files,
  so nothing on disk keeps their IDs unique.
  Define each once, as `- AC-020:` at the start of a line
  in its objective's `## Acceptance criteria`;
  `grep -l '^- AC-020:' entries/O-*.md` finds its objective,
  and is never defined twice.
  Elsewhere, such as in evidence, do not start a line with `AC-020:`.
- IDs do not name their parent.
  Tasks and criteria keep their IDs if they move to another objective:
  code comments, commit messages and logs refer to them.
- One session writes the record at a time.
  Sequential IDs depend on it.
  If parallel writers become normal,
  give each its own range of numbers.
- Write IDs in full, never as ranges such as `T-028 to T-031`,
  so that a search for any of them finds every mention.

## Types

### Objectives (`O-`)

An outcome with observable acceptance criteria and how each is checked.
Statuses: `proposed`, `active`, `paused`, `long-term` (not scheduled),
`completed`, `cancelled` (with the reason).

```markdown
## Outcome
The robot cooks a stack of pancakes without anyone touching the pan.

## Acceptance criteria
- AC-020: Each pancake is flipped exactly once.
  Check: `pytest tests/test_flip`; flip count in the log.
- AC-021: No pancake leaves the pan raw in the middle.
  Check: user eats the third pancake.

Evidence: AC-020 by T-053.

## Tasks
- T-052: Heat the pan evenly.
- T-053: Flip when the bubbles stop rising.

## Notes
What the objective's tasks need to know, such as user decisions on scope.

## Delivered
On completion: what was delivered, where (paths, commits),
what was left out or not verified, and the evidence for each criterion.
```

`## Tasks` lists the objective's tasks in their planned order,
with what each is for, but without statuses:
the task files hold those.
A criterion that moves to another objective keeps its ID;
log the move.

### Tasks (`T-`)

An ordered, independently checkable step toward one objective.
Statuses: `todo`, `in_progress`, `blocked` (name the blocker in `depends`),
`done` (with evidence), `cancelled` (with the reason).

```markdown
## Scope
What the task covers, when the summary cannot say it in one sentence.

## Done when
Tests on recorded videos flip at the right frame, and never twice.

## Notes
What the work needs: findings from other tasks with their source,
such as "From T-052: the pan needs two minutes to heat."

## Evidence
2026-10-16, sandbox without the camera:
`pytest tests/test_flip` 31 passed on recorded videos.
Code: `ae1950b`.
```

A task stays `in_progress` while one of its decisions awaits the user,
unless no other work on it is possible;
then it is `blocked`, with the decision in `depends`.
A task that moves to another objective keeps its ID:
change `objective`, update both objectives' `## Tasks`, and log it.

### Decisions (`D-`)

A material choice, including what was rejected,
so that later sessions do not rediscover dead ends.
An approach dropped without a formal decision
is a decision with status `rejected`.
Statuses: `proposed`, `awaiting_user` (with the question and `asked`),
`accepted`, `rejected` (with the reason),
`deferred` (with `revisit`),
`superseded` (with `superseded_by`).

```markdown
## Question
The question as asked, with the recommendation.

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

While `awaiting_user`, the `summary` states the question.
Once decided, `## Question` stays as asked,
the `summary` states the answer,
and the log says the summary was rewritten.

### Constraints (`C-`)

A rule the work must follow.
Statuses: `active`, `retired` (with the reason).
The body states the rule;
`source` says where it comes from.
Project conventions the user states,
such as how to split commits or which skill to load for some tasks,
are constraints, or belong in `AGENTS.md`,
not in `Handoff` or `Next action`.
Retire a constraint when an `AGENTS.md` file or skill
takes over the same rule.

### Assumptions (`A-`)

A belief the plan depends on.
Statuses: `unverified`, `holds`, `failed` (with what to do instead),
`retired`.

```markdown
## Belief
The camera sees the whole pan from above.

## Why it matters
Bubble watching (T-053) needs all four edges.

## Check
`flipbot camera --snapshot` shows all four edges.

## Results
2026-10-26: all four edges visible.
```

## What goes where

| Content | Where |
| --- | --- |
| Current state and what was learned | The entry it describes, edited in place |
| Evidence, quoted user decisions | The entry they justify |
| A finding one task makes for another | The entry that will use it, citing its source |
| Events: status changes, decisions taken, renames, runs | `log/<YYYY-MM-DD>.md`, one line each |
| Where work stands, the next step | `Status` and `Next action` in the index |

When an edit rewrites something meaningful,
log what changed,
so that the record keeps its history without git.

Log files are data, not prose:
each event is one physical line, never wrapped,
so that `grep -H T-053 log/*.md` shows whole events,
with the date in the file name.
Each file starts with `# Log: <YYYY-MM-DD>`.

## Data files

`data/<ID>/` holds files that the entry `<ID>` needs
and that are not part of the code base:
spikes, scripts to run by hand, raw outputs, measurements.
The entry names each file, for example in its `## Evidence`.
Nothing in the code imports or tests them;
a spike that becomes code is rewritten on the code branch.
Keep them small text files, up to about 1 MB;
larger or private data stays outside the record,
and the entry says where it is and how to recreate it.
Redact real data before storing it.
Data no longer needed may be deleted,
with a log line naming the files
and where their results are summarized:
the record's summary is the authority, the data only a backup.

## Invariants

After every substantial update.
`sh record.sh check` checks those marked (c);
check the rest by reading.

1. (c) Every entry starts with the fixed lines, its `id` is its file name,
   and its `status` is one of its type's values (`check` accepts
   any type's values).
2. Every active objective has acceptance criteria, each with a check.
3. Every task names one existing objective (c),
   and appears in that objective's `## Tasks`.
4. Every `depends` names an existing entry or an external item.
5. Every `done` task and `completed` objective has evidence.
6. Every `blocked` task names its blocker in `depends`.
7. Every `deferred` decision has `revisit`,
   every `superseded` one `superseded_by`,
   every `awaiting_user` one `asked` and `## Question`,
   and every `rejected` one says why.
8. `Current task` is `none` or a task that is `in_progress`,
   and `Next action` belongs to it or to the task that comes next.
9. `Next action` is one concrete, executable step
   that has not been done yet.
10. The rules block is unchanged apart from the branch name,
    and `record.sh` matches this skill's.
11. Every objective, decision, constraint and assumption
    has `applies`, naming paths when it concerns files.
12. IDs are written in full everywhere, never as ranges (c),
    and every ID mentioned has a file.
13. (c) Log lines are only in `log/`, one physical line each.
14. Every directory under `data/` belongs to an existing ID,
    and every file in it is named by that entry.
15. No secrets or credentials appear.
16. Every acceptance criterion ID is defined once.
