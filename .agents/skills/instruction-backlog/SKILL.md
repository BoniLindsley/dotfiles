---
name: instruction-backlog
description: >
  Record corrections and lessons about agent instructions as they are found,
  in a project-local backlog, `.meta/instruction-backlog.md`,
  so that changes to skills and AGENTS.md files,
  which agents may not edit, can be made later.
  Open entries in the user's words apply in the project until resolved.
  Use whenever the user corrects the agent, rejects an approach
  or repeats an instruction,
  whenever a skill or AGENTS.md proves wrong, missing, unclear
  or in conflict with another instruction,
  whenever `.meta/instruction-backlog.md` exists in the project,
  and when the user asks to review or apply pending instruction changes.
metadata:
  version: 1.0.0
---

# Instruction backlog

Skills and the user's `AGENTS.md` are usually read-only to agents,
and a project's `AGENTS.md` changes only with the user's approval.
Lessons about them are easy to lose:
by the end of a session the user's exact words are gone,
and the next session repeats the mistake.

The instruction backlog keeps each lesson as it is found,
with the change it suggests,
so that the user can apply it later,
and so that agents in the meantime can follow it.

## Where things go

| What was found | Where it goes |
| --- | --- |
| Applies only to the current work | The objectives record, if there is one |
| A change to a skill, the user's `AGENTS.md`, or the project's `AGENTS.md` | The instruction backlog |

Agent memory is read only by one tool,
so do not use it in place of the backlog.

## The backlog file

The backlog is `.meta/instruction-backlog.md`,
with `.meta/` at the root of the project,
or in the working directory without one.
`.meta/` holds agent state for the project.
In git, keep it out of commits
through `.git/info/exclude`, not `.gitignore`,
adding the line only if it is missing:

```sh
exclude="$(git rev-parse --git-common-dir)/info/exclude"
grep -qxF '/.meta/' "$exclude" || echo '/.meta/' >> "$exclude"
```

`git clean -fdx` deletes excluded files, so it would delete the backlog.
Warn before running it.

Do not keep it in `/tmp`, a scratchpad or another temporary directory.
If it cannot be written,
say so and give the entry in the reply instead.

Start a new backlog with this header,
so that it is usable without this skill:

```markdown
# Instruction backlog

Pending changes to skills and AGENTS.md files,
recorded as found, following the instruction-backlog skill.
Read this file at the start of a session.
Open entries quoting the user are their instructions for this project
until resolved.
Entries are never deleted: resolved ones move to `Resolved`.

## Open

## Resolved
```

## Read it

At the start of a session, and again after compaction,
if the backlog exists, read it.
`.meta/` is hidden and excluded from git,
so check for it with `ls -a` rather than relying on a listing.
Each entry's `When` line says in which situation it applies.
Follow open entries that quote the user,
as the user's instructions for this project,
over the skill or file they target,
until the target is changed.
Other open entries are proposals: take them into account,
but the current instructions still apply.

## Record as found

Add an entry when it happens, not at the end of the session:

- the user corrects the agent, rejects an approach,
  or repeats an instruction;
- a skill or `AGENTS.md` turns out to be wrong, missing, unclear,
  out of date, or in conflict with another instruction;
- following an instruction cost real effort
  that a better instruction would have saved.

Keep an entry only if a future agent would act differently because of it.
If an open entry already covers it, add to that entry.

Each entry is a heading under `## Open`,
with its ID, status and target on one line,
so that a search finds it from the heading alone:

```markdown
### I-004 `[open]` skill:objectives-record

- When: the objectives index grows past a few hundred lines.
- Found: user, 2026-10-27, on an index of 1000 lines:
  "Keep the index short."
- Change: summarize long decisions in the index,
  with details in `details/D-xxx.md`.
```

- **ID:** `I-` and a number, permanent, never reused.
  IDs are unique only within one project.
- **Status:** `open`, `drafted` (with the draft's path
  and the version it starts from),
  `applied` (with the date), `dropped` (with the reason).
- **Target:** `skill:<name>`, `user:AGENTS.md`
  for `~/.agents/AGENTS.md`, or `project:AGENTS.md`.
  The narrowest file that every agent needing the lesson reads.
- **When:** the situation in which the entry applies,
  so that an agent can tell whether it matters to the work at hand.
- **Found:** what happened; a correction in the user's words, dated.
- **Change:** the suggested change, as exact as is known.
  It can be left for later.

Keep entries to a few lines, with no files of their own.
An entry that needs more is probably several entries.

Find open entries for one target across projects:

```sh
find ~ -path '*/.meta/instruction-backlog.md' \
  -exec grep -H '^### I-.*`\[open\]` skill:objectives-record' {} +
```

Do not interrupt the user's request to discuss entries.

## Resolve

When the user asks to address the backlog:

1. Group open entries by target and propose each change.
2. Ask whether to write a modified version in `.meta/drafts/`,
   in a directory named after the target,
   instead of updating the file in place.
   Never edit a skill or `AGENTS.md` without the user's approval.
3. Follow the target's own conventions:
   its version, its maintenance rules,
   the agents-md-maintainer skill for a project's `AGENTS.md`.
4. Mark each entry `drafted`, `applied` or `dropped`.
   A `drafted` entry names the draft and the version it starts from,
   for example "drafted: `.meta/drafts/objectives-record/`, from 4.0.0".
   Move `applied` and `dropped` entries to `Resolved`.

Never store secrets, credentials or tokens in the backlog.
