# Entry files

Every objective, task, decision, constraint and assumption
is one file, `entries/<ID>.md`.
It starts with a header of fixed keys
that says what it holds without reading further,
so that one search covers all entries:

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
  `summary` is one sentence; `list.awk` shows it in `Open entries`.
- `objective`: the parent of a task. Exactly one ID.
- `depends`: for a task, the IDs or external items it waits for.
- `size`: for a task, `XS`, `S`, `M` or `L` (split before starting).
- `applies`: the paths, modules or topics the entry constrains
  or delivered, so that an agent can tell whether its work touches them.
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

Examples:
`grep -l '^objective: O-008$' entries/T-*.md` lists the tasks of O-008;
`grep -l '^applies:.*flipbot/flip' entries/*.md`
lists entries that cover a path.

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
Criteria take record-wide IDs, like entries,
each defined once in this form, at the start of a line,
so that searches find it.
A criterion that moves to another objective keeps its ID;
log the move.

### Tasks (`T-`)

An ordered, independently checkable step toward one objective.
Statuses: `todo`, `in_progress`, `blocked` (name the blocker in `depends`
or `## Notes`), `done` (with evidence), `cancelled` (with the reason).

```markdown
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
While `awaiting_user`: the question as asked, with the recommendation.

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

### Constraints (`C-`)

A rule the work must follow.
Statuses: `active`, `retired` (with the reason).
The body states the rule;
`source` says where it comes from.
Project conventions the user states,
such as how to split commits,
are constraints, or belong in `AGENTS.md`,
not in `Handoff`.

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
| Events: status changes, decisions taken, renames, runs | `log/<YYYY-MM-DD>.md` |
| Where work stands, the next step | `Status` and `Next action` in the index |

When an edit rewrites something meaningful,
log what changed,
so that the record keeps its history without git.
