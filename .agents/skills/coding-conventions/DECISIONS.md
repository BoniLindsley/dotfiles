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
- **D-3** `[superseded]` by D-4: Summaries at the top of files,
  in projects that keep them.
  - Change: "Summarize Files", a section of four points;
    one line in the description.
    Left out: a fixed marker such as `Summary:` for grep,
    which would clash with docstrings and `//!`,
    since `head` reads the first lines without one;
    a script checking that summaries are present,
    which belongs to a project that adopts them, not to the skill.
    Read with `head -n 5`, not `-n 3`, and the summary ends by line 5:
    a shebang, an encoding line or a docstring's opening quotes
    can come before three lines of summary.
  - Reason: user, 2026-11-14: "Start files with code that accept comments
    with a short summary agent will find helpful
    similar to how a description frontmatter is used to determine relevance.
    While not a widely used convention,
    this can be good for self controlled codebases."
    Opt-in per project, because the skill loads in every task,
    and summaries in a codebase not the user's own
    would be noise to its maintainers.
    A summary describes *what*, unlike other comments,
    which the skill keeps to *why*:
    it stands in for reading the file, not for reading the code.
    Its accuracy cannot be enforced in code,
    so it names the responsibility, which changes least,
    and reviews check it.
- **D-4** `[accepted]` Summaries behind a key, only where needed.
  - Change: "Summarize Files" rewritten:
    a summary only where a file's name and place leave its purpose unclear;
    placed after a shebang, `#pragma once` or an include guard;
    a first line after `responsibility:` that stands alone,
    and lines of detail after it starting with `|- `;
    line comments, not docstrings; surveys by `git grep`.
    Left out: the key `description:`, as skills use,
    which invites listing the contents;
    `responsibilities:`, whose plural invites a list;
    an indent for detail lines, which only `awk` reads;
    `>> `, which starts C++ lines continuing a stream expression;
    `\- `, as Vimscript continues lines,
    which needs escaping in every pattern, a mistake there finding nothing,
    shows as `-` in Markdown, and warns in Python strings;
    `|- ` without its space, which Markdown tables' separators match.
  - Reason: user, 2026-11-14, on D-3's summaries ending by line 5:
    "Not flexible enough.
    Consider having a `grep`-able prefix in the first few lines instead."
    "Not every source file needs this.
    Agents can still fallback to searching without.
    And the implicit `.hpp`, `.cpp` relationship should be relatively clear."
    "Consider using `description` to match skills,
    or `responsibilities` for precision."
    "After `#pragma once`, header guards and shebangs."
    "Use `|-`."
    `head -n 5` over 130 files gave 909 lines, 730 of them includes,
    blank lines and file banners; the key gives one line per summary,
    and lets a test check summaries' form.
