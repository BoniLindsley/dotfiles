# Decisions: AGENTS.md

Why the user's AGENTS.md is as it is,
and changes that were rejected.
Read before proposing a change to it; not needed to use it.
Records start on 2026-10-27; earlier reasons were not kept.

- **D-1** `[accepted]` Find the objectives record
  with `ls -a .meta` and `git worktree list`.
  - Change: the start-of-session step runs both,
    and defers older record locations to the objectives-record skill.
  - Reason: a record of an older version, checked out elsewhere,
    was found only through `git worktree list`;
    the step named only the newest location.
    Found by an agent, 2026-10-27.
