# Decisions: python-style

Why this skill is as it is,
and changes that were rejected.
Read before proposing a change to it; not needed to use it.
Records start on 2026-11-15; earlier reasons were not kept.

- **D-1** `[accepted]` 1.0.0: No "passive" wording.
  - Change: "This skill is passive, to be applied in future requests,
    and no immediate action is expected from loaded." removed;
    version 1.0.0 added.
  - Reason: user, 2026-11-15, asked whether to keep load-behaviour clauses
    for invocation without paths:
    "Leave them out."
    And: "I have not noticed issues with random styling edits
    outside existing edit scope."
    A skill with nothing to apply to is passive already,
    and agents keep to the scope of their task without it.
    Invoked bare after writing files, "no immediate action"
    could stop an agent applying the skill to what it just wrote.
