# `taskmd` File Format Specification

**Version:** 0.1.0
**Status:** Draft (Phase 1 — covers task/clock/update syntax; scheduling
extension described in §7 is specified but not yet implemented in the
parser)

This document is the canonical, versioned reference for the `taskmd` file
format. It defines the on-disk Markdown syntax only. Parser behavior,
library APIs, and CLI commands are described in separate documents /
modules and are not normative here except where they affect what a
conforming file must look like (e.g. strict vs. lenient parsing rules).

---

## 1. File identification

A file is recognised as a `taskmd` file if either of the following holds:

1. Its filename ends in `.task.md`, or
2. It is a `.md` file whose **first line** is exactly:

   ```
   <!-- taskmd -->
   ```

The HTML comment form is valid Markdown and renders invisibly in any
Markdown viewer, so a `taskmd` file identified this way still degrades
cleanly when opened in a tool that doesn't understand `taskmd`.

Using the `.task.md` extension is the preferred approach for new files,
since editors that don't know about `taskmd` still recognise the `.md`
suffix and fall back to standard Markdown syntax highlighting and
rendering.

---

## 2. Top-level structure

A `taskmd` file contains zero or more **task headings** at any Markdown
heading level (`#` through `######`). The heading level establishes the
parent/child (task/subtask) relationship: a heading is a subtask of the
nearest preceding heading with a strictly shallower level.

```markdown
# TODO Write the parser :python:core:
# DONE Add logging :core:
## TODO Handle edge cases
```

In the example above, "Handle edge cases" is a subtask of "Add logging"
because it is one level deeper and immediately follows it.

---

## 3. Task heading syntax

```
{HASHES} {STATUS} {TITLE} [:{TAG}:{TAG}:...]
```

| Component | Rule |
|---|---|
| `{HASHES}` | One or more `#` characters. Depth determines nesting. |
| `{STATUS}` | One of `TODO`, `DONE`, `DROP`, `WAIT`. Case-sensitive in strict mode; case-insensitive in lenient mode. |
| `{TITLE}` | Free text. Must not itself end in something that parses as a tag block unless a tag block is intended. |
| Tag block | Optional. Must be the last token on the line: `:tag1:tag2:...`. |

### 3.1 Tags

- Tags appear only in heading lines, after the title.
- The tag block is a colon-delimited list surrounded by colons on both
  sides, e.g. `:a:b:c:`.
- A heading with no tags has no trailing colon block at all.
- Tag characters are restricted to lowercase alphanumerics plus `-` and
  `_`.
- Tags are **inherited downward** for reporting and filtering purposes: a
  subtask inherits every tag carried by its ancestors. Inherited tags are
  computed at read time and are never physically duplicated in the file.

---

## 4. Task body sections

Immediately following a task heading, and before the next heading of
equal-or-shallower depth, the following sections may appear, always in
this order:

1. A description block
2. Zero or more update sections
3. Zero or more clock entries
4. Zero or more subtask headings (deeper level)

Update sections and clock entries may be interleaved with each other in
practice (they are just headings), but conceptually each is independent.

### 4.1 Description block

Any paragraphs and ordinary Markdown content appearing directly after the
task heading, before the first sub-heading, is the task's description —
its initial requirements or notes.

### 4.2 Update sections

A sub-heading whose text is **not** a status keyword line and **not** a
`CLOCK:` line is a freeform update entry. An optional ISO 8601 timestamp
(with required timezone offset) may appear as the very first token of the
heading text:

```markdown
### 2025-06-10T14:30+02:00 Progress update
Work continued on the tokeniser.
```

If no timestamp is present, the update simply has no recorded time.

Timestamp rules:

- Must be ISO 8601 with an explicit timezone offset (e.g. `+02:00` or
  `Z`) when written by `taskmd` itself.
- **Strict mode:** a timezone-less datetime is a parse error.
- **Lenient mode:** a timezone-less datetime is accepted with a warning,
  and the local system timezone is assumed.

### 4.3 Clock entries

A sub-heading of the form:

```
### CLOCK: [DATETIME]--[DATETIME] [DESCRIPTION]
```

records a closed time-tracking session. An **open** (currently running)
session omits the second datetime but keeps the `--`:

```
### CLOCK: [DATETIME]-- [DESCRIPTION]
```

| Component | Rule |
|---|---|
| `DATETIME` | ISO 8601 datetime with required timezone offset, e.g. `2025-06-10T14:30:00+02:00` or `2025-06-10T12:30:00Z`. Seconds are optional. |
| `DESCRIPTION` | Optional free text after the second timestamp (or after the lone timestamp for an open session). |

Body paragraphs beneath a `CLOCK:` heading are work notes describing what
was done during that session.

A task may have at most one **open** clock entry at a time under normal
use, though the parser does not forbid more than one at the data-model
level — the CLI layer enforces this depending on mode (see the
strict/lenient table below).

### 4.4 Subtask headings

Any deeper-level heading matching the task heading syntax (§3) is a
subtask. Subtasks recursively contain the same body structure described
in this section (description, updates, clocks, further subtasks).

---

## 5. Strict vs. lenient mode

`taskmd` files are parsed in one of two modes. Strict mode is the default
and is recommended for files maintained solely through the `taskmd` CLI.
Lenient mode is intended for hand-edited files or files migrated from
other formats.

| Rule | Strict | Lenient |
|---|---|---|
| Status keywords | Case-sensitive | Case-insensitive |
| Datetime format | ISO 8601 only | A small fixed set of common ISO-8601-like formats (no external dependency); anything else is a parse error |
| Timezone in datetime | Required; error if absent | Warning + assume local tz |
| Unclosed `CLOCK:` | Warning only | Silently accepted |
| Unknown heading in task body | Error | Treated as an update section |
| Missing `--` in `CLOCK:` | Error | Best-effort parse |

Lenient-mode warnings are collected rather than raised; conforming
parsers should surface them to the caller without aborting the parse.

---

## 6. Worked example

```markdown
# TODO Write the parser :python:core:
Implement the two-stage scanner/builder described in the design doc.

### 2025-06-09T09:00+02:00 Kickoff
Read through the design doc and sketched the token types.

### CLOCK: [2025-06-09T09:15+02:00]--[2025-06-09T11:00+02:00] Initial scaffolding
Set up the module layout and stub classes.

### CLOCK: [2025-06-10T09:00+02:00]-- Continuing stage 2
Working through the tree builder.

## TODO Handle edge cases
Multi-line titles, tags containing digits, empty tag blocks.

# DONE Add logging :core:
Structured logging via the stdlib `logging` module.

### CLOCK: [2025-06-05T13:00+02:00]--[2025-06-05T14:30+02:00]
```

In this example, "Handle edge cases" is a subtask of "Write the parser"
and inherits the `python` and `core` tags for reporting purposes even
though it declares no tags of its own.

---

## 7. Scheduling extension: `EVENT` entries

This is an additive extension to the format. It does not change the
meaning of any existing task, update, or clock syntax.

### 7.1 EVENT heading syntax

```
{HASHES} EVENT [DATETIME--DATETIME] {TITLE} [RECUR {RULE}] [:{TAG}:{TAG}:...]
```

| Component | Rule |
|---|---|
| `EVENT` | Literal keyword, case-sensitive in strict mode. |
| `[DATETIME]--[DATETIME]` | Mandatory scheduled span. Both ends required. Same timezone-required ISO 8601 rules as `CLOCK:`. |
| `{TITLE}` | Free text describing the event. |
| `RECUR {RULE}` | Optional inline recurrence rule (§7.3), placed after the title and before the tag block. |
| Tag block | Same `:tag1:tag2:` syntax as tasks. |

Example:

```markdown
## EVENT [2025-09-01T10:00+01:00]--[2025-09-01T11:00+01:00] Sprint planning :meeting:
## EVENT [2025-09-03T09:00+01:00]--[2025-09-03T11:00+01:00] Focus: parser work RECUR +1w :block:
```

### 7.2 EVENT body structure

An `EVENT` may contain, in order: a description block, `CLOCK:`
sub-headings recording actual attendance/work spans, update sub-headings
for post-event notes, and deeper `EVENT` headings as sub-events (e.g.
agenda items). `EVENT` entries may also be nested directly inside a task
heading, which links allocated time to that task.

### 7.3 Recurrence rules

```
RULE      := PREFIX INTERVAL UNIT [WEEKDAYS] [UNTIL]
PREFIX    := "+"   -- shift from last occurrence (catch-up style)
           | "++"  -- shift from original anchor (fixed-cadence style)
           | ".+"  -- shift from today if anchor is in the past
INTERVAL  := integer >= 1
UNIT      := "d" | "w" | "m" | "y"
WEEKDAYS  := weekday selector, only valid with unit "w" or "m"
UNTIL     := "@" ISO-8601-date
```

Weekday selectors: `MON`…`SUN` (named days), `MON,WED` (comma-separated
list, unit must be `w`), `2MON` (second Monday of the month, unit must be
`m`), `-1FRI` (last Friday of the month).

In strict mode an unrecognised rule string is a parse error; in lenient
mode it is stored as a raw string with a warning.

---

## 8. Versioning of this document

Changes to this spec that add new syntax (e.g. §7) are additive and
backward compatible: existing `taskmd` files remain valid. Changes that
alter the meaning of existing syntax will bump the major version and be
called out explicitly at the top of this document.
