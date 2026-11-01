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
- **D-4** `[accepted]` 5.3.0: Log lines only in daily files.
  - Change: `log/<YYYY-MM-DD>.md`, one file per day;
    no `## Log` section in the index; invariant 16;
    the rules block changes; conversion from 5.0 to 5.2.
  - Reason: an index log of about 85 lines was read every session
    and used for no decision. User, 2026-10-30:
    "Is the log usually used? Consider splitting the logs by day
    instead, and may be always write logs outside of the index."
- **D-5** `[superseded]` 5.3.0, replaced by D-6 in 6.0.0:
  Always archive finished tasks
  and objectives, each in a commit of its own.
  - Change: done tasks and completed or cancelled objectives move
    to detail files in the commit right after the one that marks them,
    changing nothing else; invariant 15; the rules block changes;
    "Finishing" archives after the final merge.
  - Reason: an index reached 563 lines with done tasks still in it,
    since they moved only "once their notes are no longer needed".
    User, 2026-10-30: "Consider changing the skill to always archive
    completed tasks and objectives." And: "Consider having task and
    objective update commits, such ask marking as completed,
    as separate commit from archiving them,
    so the last update before archiving is easily seen."
- **D-6** `[accepted]` 6.0.0: One file per entry; the index lists
  open entries rebuilt from their headers.
  - Change: `entries/<ID>.md` for every objective, task, decision,
    constraint and assumption, authoritative over the index;
    `list.awk` rebuilds `Open entries`; only `Status`, `Next action`,
    `Handoff` and `Artifacts` are hand-written; objectives list their
    tasks in order without statuses; rejected approaches are
    decisions; header rules for searching (one key per line,
    a parent key `objective`, IDs in full, never ranges);
    nothing moves when work finishes, replacing D-5's archive commits;
    `details.md` becomes `entries.md`; invariants rewritten.
  - Reason: a 413-line index was about half irrelevant to the next
    task, and archiving still moved entries. User, 2026-10-30:
    "what about always storing objective information in the details
    directory? This avoids moving." Then: "Objectives and tasks all get
    their own files. [...] If status drift apart, I would expect the
    details files to be more up to date." And: "This looks more and
    more like a database than a document, which is fine."
    Rejected: one file per objective holding its tasks
    (done tasks accumulate; still moves); a stored index of tasks by
    parent (searchable from headers, and would drift).
- **D-7** `[accepted]` 6.0.0: Logs hold events; entries hold state.
  - Change: log lines record events naming full IDs, in daily files;
    entries hold current state and findings, edited in place,
    with meaningful rewrites logged; a finding goes to the entry
    that will use it, citing its source; conventions become
    constraints, not `Handoff` items.
  - Reason: an earlier proposal appended dated notes to entry files.
    User, 2026-10-30: "Not sure about keeping logs in decision or
    details file. Are logs not mostly events that happened?"
- **D-8** `[accepted]` 6.0.0: ID allocation.
  - Change: entries with files get record-wide IDs, the next from
    `entries/` and `log/`, created only if no file exists; acceptance
    criteria keep record-wide IDs (`AC-020`), defined once as
    `- AC-020:` in their objective, with an invariant for duplicates;
    one session writes the record at a time.
  - Reason: user, 2026-10-30: "How would IDs be kept unique for other
    types such as AC?" and "Is a similar numbering pattern relevant
    for tasks?" Tasks are referenced in code and commits and may
    change objective, so parent-qualified task IDs were rejected.
    Parent-qualified criteria (`O-008.AC-1`) were drafted, then
    dropped; user, 2026-10-30: "If AC can be searched easily as with
    tasks, can they be kept without an objective ID prefix for now?"
    Studied: git-issue (one directory per issue, status as a tag,
    no stored index); not copied: identity and dates from git history.
- **D-9** `[superseded]` 6.1.0, narrowed by D-12 in 6.2.0:
  `record.sh` replaces `list.awk`.
  - Change: one POSIX shell helper per record with `list`, `update`
    (rewrites `Open entries` in place), `check` (the invariants a
    script can check), `applies <path>` (entries naming the path or a
    directory above it) and `next <prefix>`; the rules block and
    session loop use it.
  - Reason: a test session had to write its own loops to check the
    record and to splice the list into the index, and four searches to
    find what applied to one file (backlog, 2026-10-30, after a test
    report). User, 2026-10-30: "Draft the change." The checker found a
    real ID range left by the 6.0.0 conversion.
- **D-10** `[accepted]` 6.1.0: Log events take one physical line.
  - Change: never wrapped, as data rather than prose,
    so `grep` shows whole events; the date stays in the file name.
  - Reason: wrapped log entries showed only their first line in
    `grep -H T-029 log/*.md` in the test session.
- **D-11** `[accepted]` 6.1.0: Smaller SKILL.md; clarified entries.
  - Change: IDs, data files and invariants move to `entries.md`,
    commits and merges to `git-setup.md` (SKILL.md 515 to about 300
    lines); tasks gain `## Scope`; a decision's lifecycle
    (`## Question` stays, summary from question to answer, task
    `blocked` only if no other work is possible); `applies:` paths
    relative to the repository root; `Current task` only an ID or
    `none`; `Waiting on the user` allows reviews and answers owed;
    conventions such as skills to load are constraints; tests rerun
    at start only when something changed; conversion from 6.0.
  - Reason: the test session's friction report (2026-10-30): SKILL.md
    was the largest fixed cost at session start; the other points were
    guesses it had to make.
- **D-12** `[accepted]` 6.2.0: A fixed entry start instead of a checker.
  - Change: every entry starts with `---`, `id:`, `status:`,
    `summary:`, and for tasks `objective:`, so `record.sh` reads them
    by position; the index holds no `Open entries` (agents run
    `sh record.sh list`), so nothing can drift; `record.sh` keeps
    `list`, `applies`, `next` and a `check` of the fixed lines,
    task objectives, ID ranges and log line format (154 to 78 lines);
    `update` and the other checks go; monthly log files are split into
    daily files on conversion instead of being kept; conversion paths
    from 5.3.0, 6.0.0 and 6.1.0 are dropped, since those versions were
    never used outside the session that made them.
  - Reason: user, 2026-10-30: "The `record.sh` script is complicated.
    Can record format be enforced better to make it simpler?" and
    "You may assume version migration is not necessary for versions
    created by this session."
  - Rejected: rules for marking a task done without meeting
    `Done when`, for answers that pick no option, and for
    `Last verified` after partial checks. They came from a test that
    staged those situations. User, 2026-10-30: "Are those really worth
    putting in the instructions? Feels adversarial if an agent wants to
    do that."
- **D-13** `[accepted]` 6.2.1: The description says only when to load.
  - Change: the description names only what the skill keeps
    and when to load it: an objective unlikely to finish
    in one session, work stopping to be resumed later,
    or an existing record, by the names that show one:
    OBJECTIVES.md, `.meta/objectives`, `.objectives`
    and `meta/*/objectives`.
    It drops the index and entry files, the git branch,
    its merges and its checkout location, long gaps between sessions,
    and the former name.
    `When to use` goes, as does the opening sentence
    repeating the description; the body opens with the aim.
    The overview states as "when X, do Y" that finished entries
    stay in place and only unneeded data is deleted.
  - Reason: user, 2026-10-30: "There is a lot of implementation detail
    in its description." The former name only mattered for conversion,
    which is started on purpose and reads `lifecycle.md`.
    User, 2026-10-30: "Migration can be explicitly triggered
    if necessary, which will necessitate reading related documents."
    The body is read only after the description has matched,
    so repeating when to use the skill there adds nothing.
    User, 2026-10-30, on the opening paragraph:
    "The whole paragraph largely repeats the header information."
    The wording of the first two lines and the stop condition
    are the user's, 2026-10-30: "Keep work resumable across
    interrupted sessions with a record of objectives, tasks and
    decisions. Use when an objective is unlikely to finish in one
    session, a session is interrupted, or whenever OBJECTIVES.md [...]"
    The overview kept its rule against moving and deleting,
    since agents tidy finished items away by habit and D-5 once
    archived them, but its double negative was hard to read.
    User, 2026-10-30: "Conditional negative instructions feel harder
    to follow. "When X, do Y" is probably simpler for agents."
  - Rejected: "a session is interrupted" as worded; an agent learns
    of a sudden interruption only once it can no longer write,
    so the condition is work stopping to be resumed later.
    Long gaps, costly context, and "the user asks for persistent
    or resumable tracking" as reasons, and an exception for trivial
    one-session work: long gaps imply several sessions,
    costly context comes with them, asking for a skill's work
    loads it anyway, and trivial work fails the first condition.
