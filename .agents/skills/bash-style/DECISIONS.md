# Decisions: bash-style

Why this skill is as it is,
and changes that were rejected.
Read before proposing a change to it; not needed to use it.
Records start on 2026-11-15.

- **D-1** `[accepted]` 1.0.0: The skill, from `bin/dockered-claude`.
  - Change: a new skill describing the layout and rules
    of `bin/dockered-claude` in the dockered-claude project,
    which `.meta/apply-skill-drafts` there was rewritten to follow.
  - Reason: user, 2026-11-15: "update `.meta/apply-skill-drafts`
    script style to be similar to `bin/dockered-claude`
    in the sense of how it splits `main`, `run`, `parse_aguments`,
    calling into `main`, and other rules you may derive.
    Create a skill for this to be applied in future scripts,
    taking inspiration for the other language styling skills."
  - Reason: `run` taking explicit parameters,
    with `main` parsing and forwarding to it,
    follows python-style.
    `bin/dockered-claude` has no `run`:
    its `main` calls each step itself,
    since its steps share much state and branch by mode.
  - Reason: the opening paragraph for invocation with file paths
    and no load-behaviour wording follow cpp-style D-1.
