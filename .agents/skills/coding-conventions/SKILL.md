---
name: coding-conventions
description: >
  General code annotation preferences, language-agnostic.
  Apply when writing or reviewing code in any language.
  Covers when to add explanatory comments for non-obvious decisions,
  and when to add TODO markers for uncertain choices.
  Passive by default
  -- no action needed on load unless file paths are provided.
---

## Behaviour on Load

- **No paths given:**
  Internalize these preferences
  and apply them to all code written going forward.
  No immediate action required.
- **Paths given:**
  Review the specified files.
  Add explanatory comments to non-obvious decisions
  and `TODO` markers to uncertain ones.
  Do not modify logic unless separately instructed.

## Annotate Non-Obvious Decisions

If a choice required deliberate reasoning
that would not be immediately apparent to a reader,
add a comment explaining *why* — not just *what*.

**The test:** would a competent reader likely pause
and wonder why this decision was made?
If yes, comment it.

```cpp
// Using index-based loop instead of range-for:
// iterator invalidation is possible here
// if the container is modified during traversal.
for (std::size_t i = 0; i < items.size(); ++i) { ... }
```

Do not comment self-evident code.

```cpp
// BAD: redundant
x = x + 1; // increment x

// GOOD: nothing to explain
x = x + 1;
```

## Mark Uncertain Decisions with TODO

If a decision was made without high certainty
-- for example, to avoid being blocked
or because full information was unavailable
-- mark it with a `TODO` comment so it can be revisited.

**Format:**

```
// TODO: <what to check or reconsider, and why it is uncertain>
```

**Examples:**

```cpp
// TODO: Confirm this timeout value is appropriate for production load.
constexpr int kTimeoutMs = 5000;

// TODO: Not certain this handles the empty-input edge case correctly.
if (data.size() > 0) { ... }
```

This signals to the reader:
*a choice was made here, but it deserves a second look.*
