---
name: coding-conventions
description: >
  Language-agnostic preferences for writing or reviewing code:
  when to comment on decisions, explaining why or marking TODO,
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

## Weighing Designs

- Prefer subclassing or a mixin over a wrapper
  whose methods mostly forward calls unchanged;
  wrap only to narrow or adapt an interface,
  or when the object is supplied at run time.
- Weigh designs by responsibilities and clarity, not by length.
