# Decisions: objectives-record

Why this skill is as it is,
and changes that were rejected.
Read before proposing a change to it; not needed to use it.
Records start at 5.1.0; earlier reasons were not kept.

- **D-1** `[accepted]` 5.1.0: Convert an older record
  only with the user's approval.
  - Change: until converted, follow the record's own rules block;
    "Find the record" covers older locations.
  - Reason: the skill said how to convert but not when,
    and conversion moves a worktree and rewrites the rules block,
    so it is not a routine choice.
    Found by an agent, 2026-10-27, on a 4.0.0 record under 5.0.0.
- **D-2** `[accepted]` 5.1.2: `Next action` must still be current.
  - Change: invariant 8 adds "and `Next action` belongs to it
    or to the task that comes next"; invariant 9 adds
    "that has not been done yet"; step 5 says to update
    `Current task`, `Position` and `Next action` together
    when a task changes status.
  - Reason: a task was recorded done
    while `Next action` still described it,
    and invariant 9 accepted any concrete, executable step.
    User, 2026-10-30: "Why was "Next Action" not updated?
    Does `objectives-record` need updating for this?"
- **D-3** `[accepted]` 5.2.0: Data files under `data/<ID>/`.
  - Change: a `data/` directory per ID for files a task needs
    that are not code, named by their entry; invariant 14;
    small text only, large or private data stays outside;
    data no longer needed may be deleted with a log line;
    finishing an objective decides keep or delete;
    the rules block changes.
  - Reason: a Windows spike and its outputs were kept
    in an uncommitted drafts folder, which is meant for drafts
    under review, and a cited output file went missing unnoticed.
    User, 2026-10-30: "Suggest changes to the `objectives-record`
    skill to accomodate for data files needed for tasks,
    but should not be part of the code base, as in this case."
    Rejected: listing data files in `Artifacts`;
    keeping them outside the record.
