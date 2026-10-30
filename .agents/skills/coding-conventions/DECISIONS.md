# Decisions: coding-conventions

Why this skill is as it is,
and changes that were rejected.
Read before proposing a change to it; not needed to use it.
Records start on 2026-10-30; earlier reasons were not kept.

- **D-1** `[accepted]` Subclassing over forwarding wrappers;
  designs not weighed by length.
  - Change: "Weighing Designs", two lines.
    Left out: a Python mixin constructor signature,
    too specific for a skill loaded in every task.
  - Reason: an agent recommended a wrapper forwarding every method
    over a mixin because it was shorter.
    User, 2026-10-29: "Line count is not an issue.
    I am not a fan of forwarding,
    when that is what subclassing is supposed to be for.
    It drowns the responsibility of a class
    within scaffolding methods."
    Kept to two lines with exceptions,
    so that it fires only when a wrapper would mostly forward,
    and does not become noise in other tasks.
- **D-2** `[accepted]` One section on commenting decisions;
  no load behaviour.
  - Change: the two comment sections merged into one test
    with three cases (settled, not settled, obvious);
    "Behaviour on Load" reduced to one line for reviews,
    which now report design concerns;
    "Passive by default" removed from the summary.
  - Reason: user, 2026-10-30: "is the behaviour on load instructions
    necessary? Are the two sections about commenting with decisions
    overlapping or somewhat redundant?"
    The no-paths case restated what loading means,
    and summaries cost context in every task.
