# Detail files

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
