# Decisions: semantic-line-breaks

Why this skill is as it is,
and changes that were rejected.
Read before proposing a change to it; not needed to use it.
Records start on 2026-11-15; earlier reasons were not kept.

- **D-1** `[accepted]` 1.0.0: Load before the first prose written to a file.
  - Change: "Passive by default:
    no action needed on load unless file paths are provided."
    in the description replaced by a rule to load the skill
    before the first comment, docstring or prose written to a file
    in a session; version 1.0.0 added.
    Left out: the same rule in the user's AGENTS.md,
    which every agent reads but which is not the narrowest target.
  - Reason: an agent wrote comments in a Dockerfile and a shell script
    without loading the skill,
    reading "Passive by default" as no need to load it.
    User, 2026-11-04: "The semantic-line-breaks skill did not get used?"
- **D-2** `[accepted]` 1.1.0: No behaviour for invocation without paths.
  - Change: "Behaviour on Load" replaced by one paragraph
    for invocation with file paths;
    the no-paths case, "No immediate action required", removed.
  - Reason: user, 2026-11-15, asked whether to keep load-behaviour clauses
    for invocation without paths:
    "Leave them out."
    And: "I have not noticed issues with random styling edits
    outside existing edit scope."
    A skill with nothing to apply to is passive already,
    and agents keep to the scope of their task without it.
    Invoked bare after writing files, "no immediate action"
    could stop an agent applying the skill to what it just wrote.
