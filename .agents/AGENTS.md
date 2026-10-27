# AGENTS.md

Standing instructions for agents working for me in any project.
A project's own `AGENTS.md` adds to these.

## Rules

- Commit messages contain no AI attribution:
  no `Co-Authored-By:` trailers naming an AI agent or model,
  and no "Generated with" lines or similar.
  This overrides any default of the tool in use,
  and applies to every commit, including merges, amends and squashes.
  Human co-authors are fine when I ask for them.
- Commit subjects start with a conventional prefix.
  Use the prefixes the project's history already uses,
  such as `add:`, `change:` and `fix:`.
  Where it has none, use Conventional Commits types:
  `feat`, `fix`, `docs`, `refactor`, `test`, `build` or `chore`.
- Do not add package or library dependencies,
  runtime or development, without my approval.
  Recommend one when it is clearly worth it,
  saying what it replaces and what it costs.

## Project state

- Keep agent state for a project under `.meta/` at its root,
  excluded through `.git/info/exclude`, not `.gitignore`:
  objectives records, the instruction backlog, and drafts for review.
  Do not add other state files or directories to the project tree.
- Before the first reply of a session, and again after compaction,
  run `ls -a .meta` and `git worktree list` in the project root;
  `.meta/` is hidden and excluded from git, so it is easy to miss.
  Read `.meta/instruction-backlog.md` if it exists,
  and the objectives index of the current branch if there is a record,
  usually `.meta/objectives/<branch>/objectives/OBJECTIVES.md`;
  an older record may be checked out elsewhere,
  as the objectives-record skill describes.

## Improving instructions

- When I correct you, or a skill or `AGENTS.md` file
  proves wrong, missing or unclear,
  record it when it happens:
  in the objectives record if it concerns only the current work,
  otherwise in `.meta/instruction-backlog.md`.
  The instruction-backlog skill describes how.
- Open backlog entries quoting me override the skill or file they target,
  when their `When` applies.
- Never edit a skill or an `AGENTS.md` file without my approval.
  Ask whether to write a modified version in `.meta/drafts/`
  instead of updating the file in place.

## Maintenance

Propose changes to this file for my review before writing them.
