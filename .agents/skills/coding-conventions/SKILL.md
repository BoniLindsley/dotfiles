---
name: coding-conventions
description: >
  Language-agnostic preferences for writing or reviewing code:
  when to comment on decisions, explaining why or marking TODO,
  summaries at the top of files in projects that keep them,
  and how to weigh designs:
  subclassing over forwarding wrappers, responsibilities over length.
---

When given file paths,
review them against these preferences:
add the missing comments,
and report design concerns without changing logic.

## Comment on Decisions

Comment a decision when a competent reader
would pause and wonder why it was made.

- **Settled but not obvious:**
  explain *why*, not *what*.

  ```cpp
  // Index-based loop: the container may change during traversal,
  // which would invalidate iterators.
  for (std::size_t i = 0; i < items.size(); ++i) { ... }
  ```

- **Not settled,**
  such as made to get unblocked or without full information:
  mark it `TODO:` with what to check and why it is uncertain.

  ```cpp
  // TODO: Confirm this timeout suits production load.
  constexpr int kTimeoutMs = 5000;
  ```

- **Obvious:** no comment.

## Summarize Files

In a project that keeps file summaries, as its `AGENTS.md` says,
summarize a file whose name and place
would leave a competent reader unsure what it is for:
a vague name, an entry point,
or an implementation holding more than its header shows.
Other files need none:
agents fall back to searching,
and a `.cpp` file implements its header.

Put the summary in the file's first comments,
after anything that must come first,
such as a shebang, `#pragma once` or an include guard,
and before any code.
Its first line names the file's responsibility
after the key `responsibility:`,
and stands alone within the project's line limit,
since surveys show only that line.
Lines after it, each starting with `|- `, add detail.

```cpp
#pragma once

// responsibility: Rule-based AI for actors.
// |- Rules are checked in order when an actor's actions run out,
// |- and the first whose conditions all pass replaces its queue.
```

- Use the language's line comments, such as `#` in Python and shell,
  not a docstring, so that one pattern finds every summary.
- Name the responsibility, not the contents:
  a list of functions goes stale with the next change.
  A file that needs "and" to be summarized
  may hold two responsibilities.
- Update the summary in the change that alters the responsibility,
  and in a review, report summaries that no longer match.
- To find where something is handled,
  list the files with their summaries' first lines,
  such as with `git grep -m1 'responsibility: '` beside `git ls-files`,
  before opening any whole.

## Weighing Designs

- Prefer subclassing or a mixin over a wrapper
  whose methods mostly forward calls unchanged;
  wrap only to narrow or adapt an interface,
  or when the object is supplied at run time.
- Weigh designs by responsibilities and clarity, not by length.
