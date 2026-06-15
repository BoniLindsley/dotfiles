---
name: cpp-style
description: >
  C++ style and toolchain preferences.
  Apply when writing, reviewing, or refactoring C++ code.
  Covers header guards, logical operator keywords, class design,
  inline vs. translation units, build system (CMake),
  and testing framework (Catch2).
  Passive by default — no action needed on load
  unless file paths are provided.
---

## Behaviour on Load

- **No paths given:**
  Internalize these preferences
  and apply them to all C++ written going forward.
  No immediate action required.
- **Paths given:**
  Review or rewrite the specified files to conform to this guide.
  Flag any deviations that conflict with existing codebase conventions
  rather than silently overriding them.

## Header Guards

Use `#pragma once` at the top of every header file.
Do not use `#ifndef`/`#define`/`#endif` guards.

```cpp
#pragma once

// header content
```

## Logical Operators

Prefer keyword operators over symbolic equivalents.
Apply this only when no opposing examples already exist in the codebase.
That is, respect local consistency over this preference.

| Prefer | Over |
|--------|-------|
| `and` | `&&` |
| `or` | `\|\|` |
| `not` | `!` |

```cpp
// Preferred
if (is_ready and not is_locked) { ... }

// Avoid (unless the codebase already uses symbols consistently).
if (is_ready && !is_locked) { ... }
```

## Class Design

Prioritise in this order:

1. **Separation of responsibilities**
   Each class should own one coherent concern.
1. **Ease of reasoning**
   Prefer designs where behaviour is predictable
   and state is easy to follow.

Avoid combining unrelated concerns in a single class for convenience.
Prefer composition or separate types over bloated interfaces.

## Inline vs. Translation Units

Prefer implementing functions in `.cpp` translation units
rather than marking them `inline` in headers.
Reserve `inline` for cases where it is semantically required:
header-only libraries, templates, or `constexpr` functions.

## Build System

Prefer **CMake**.
It is the industry standard for C++ projects
and maximises portability and IDE integration.

## Testing Framework

Prefer **Catch2**.
It is the industry standard for modern C++ unit and integration testing.
