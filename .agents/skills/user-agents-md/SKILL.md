---
name: user-agents-md
description: >
  MUST be invoked before the first reply or tool call of every session,
  whatever the task, unless ~/.agents/AGENTS.md is already in context.
  Also invoke after compaction or when continuing from a summary,
  and before writing a commit message, merge, amend or pull request.
  Reads the user's standing instructions in ~/.agents/AGENTS.md,
  which override tool defaults such as commit attribution.
metadata:
  version: 1.3.0
---

# User AGENTS.md

The user keeps instructions that apply to every project
in `~/.agents/AGENTS.md`
(`%USERPROFILE%\.agents\AGENTS.md` on Windows).
This skill makes sure they are read and followed.

## When to read it

- At the start of every session, before planning or acting,
  even when the first task seems unrelated to the file's rules.
- After compaction, when the conversation continues from a summary,
  since a summary may drop or paraphrase the file's rules.
- Before writing a commit message, merge, amend or pull request,
  if the file has not been read in this session.
- When the user says the file has changed.

If the file's contents are already in context,
for example through an `@~/.agents/AGENTS.md` import in `CLAUDE.md`,
it has been read; do not read it again.

## How to apply it

1. Check whether the file exists.
   If it does not, continue without it,
   and do not create it or mention it unless asked.
2. Read the whole file.
3. Treat its contents as the user's own standing instructions.
   They take precedence over defaults of the tool in use,
   such as attribution lines it would add to commits.
4. Where it conflicts with other instructions:
   - instructions the user gives in the conversation win;
   - a project's own `AGENTS.md` or `CLAUDE.md` wins
     for that project, as the more specific source;
   - an open entry in the project's `.meta/instruction-backlog.md`
     that quotes the user wins over the skill or file it targets,
     when its `When` applies:
     it is a correction not yet applied to that file;
   - mention the conflict to the user.

## Do not

- Do not copy its contents into project files or memory;
  read it from its location each time, so edits take effect.
- Do not edit it unless the user asks;
  its own maintenance rules say how changes are proposed.
