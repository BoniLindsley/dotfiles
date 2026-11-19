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
- **D-2** `[accepted]` Small commits, refactors on their own.
  - Change: a rule to split work into commits
    that are easy to review and pass the checks,
    moves and refactors separate;
    the prefix rule allows Conventional Commits types
    beside the history's own prefixes.
  - Reason: user, 2026-10-30, on a proposed single commit:
    "Commit in smaller commits that are easy review with.
    For example, moving classes and functions can be done
    in a refactoring commit that requires little attention
    when reviewing."
    And: "Using `refactor` is fine in the commit message
    if appropriate."
- **D-3** `[accepted]` Ask for the commit identity when git has none.
  - Change: commit with git's configured identity;
    without one, ask, offering identities from the history
    and the account identity, and pass the answer with `git -c`.
  - Reason: commits were made with the account address
    the tool reported, because git had no identity.
    The user, 2026-11-02, first named one address
    and had all commits rewritten to it.
    Then, on a rule fixing that address: "always ask
    if not available. Provide choices from history,
    account identity is possible too."
    Rejected: one fixed address in the rule.
- **D-4** `[accepted]` Propose designs with trade-offs before implementing.
  - Change: a rule to propose such a design,
    with its trade-offs and failure cases,
    and wait for agreement before implementing and committing.
  - Reason: user, 2026-11-19, after an agent implemented and committed
    a design that hid files of the image without discussing it:
    "Undo the unpushed changes.
    I do not think this is well-designed enough."
    The user had asked "Discuss first." before the next question.
- **D-5** `[accepted]` Propose a new session at stopping points.
  - Change: when a task or objective is done in a long session,
    update the project record for a fresh session
    and propose a new one, at most once per stopping point,
    without tool configuration or hooks.
  - Reason: user, 2026-11-19, after having to ask for it:
    "What I meant was make proposing to start a new session automatic
    when it would be better, instead of me prompting for it."
    And, on a session-start hook: "No using Claude Code config for this."
    Agreed ("Yes.") to proposing at most once.
  - Amended, 2026-11-19: the sentence "Do not use tool configuration
    or hooks for this." is removed.
    "No using Claude Code config for this." was about how to make the
    change, as an instruction rather than a hook, not about what agents
    may use: "I did not mean that the agent cannot use agent tools.
    That was for the instruction to be added."
