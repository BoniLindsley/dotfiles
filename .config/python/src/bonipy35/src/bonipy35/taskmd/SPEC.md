# `taskmd` File Format Specification

**Version:** 0.1.0
**Status:** Draft

This document is the canonical, versioned reference
for the `taskmd` file format.
It defines the on-disk Markdown syntax only.
Parser behavior, library APIs, and CLI commands
are described in separate documents and modules
and are not normative here
except where they affect what a conforming file must look like
(e.g. strict vs. lenient parsing rules).

---

## 1. File identification

A file is recognised as a `taskmd` file if either of the following holds:

1. Its filename ends in `.task.md`, or
2. It is a `.md` file whose **first line** is exactly:

   ```
   <!-- taskmd -->
   ```

The HTML comment form is valid Markdown
and renders invisibly in any Markdown viewer,
so a `taskmd` file identified this way still degrades cleanly
when opened in a tool that doesn't understand `taskmd`.

Using the `.task.md` extension is the preferred approach for new files,
since editors that don't know about `taskmd`
still recognise the `.md` suffix
and fall back to standard Markdown syntax highlighting and rendering.

---

## 2. Top-level structure

A `taskmd` file contains zero or more tasks and events.
Their headings use levels 1–6 (`#` through `######`).
Only task and event headings establish containers:
an entry belongs to the nearest preceding task or event
at a strictly shallower level
that has not been closed by an equal-or-shallower heading.
Levels may be skipped.
For example, a level-3 task can be a direct child of a level-1 task.

Tasks may contain tasks or events.
Events may contain events, but not tasks.
Updates and clocks belong to the enclosing task or event.
They never become parents of other entries.
A heading at an equal-or-shallower level
closes that container before the heading is interpreted.

### 2.1 Heading recognition

A heading starts in column 1 with 1–6 `#` characters
followed by whitespace and heading text.
Leading indentation and Setext-style underlines do not create headings.
Trailing whitespace is ignored.
Closing `#` characters are part of the text,
rather than optional Markdown heading decoration.
Titles occupy one physical line.

Recognition is line based, including inside fenced code blocks.
Escape or indent heading-like lines in code examples
when they must remain ordinary body text.
Ordinary text before the first heading is a preamble
and does not belong to an entry.

### 2.2 Example hierarchy

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
| `{HASHES}` | One to six `#` characters. Depth determines nesting. |
| `{STATUS}` | One of `TODO`, `DONE`, `DROP`, `WAIT`. Case-sensitive in strict mode; case-insensitive in lenient mode. |
| `{TITLE}` | Free text. Must not itself end in something that parses as a tag block unless a tag block is intended. |
| Tag block | Optional. Must be the last token on the line: `:tag1:tag2:...`. |

### 3.1 Tags

- Tags appear only in heading lines, after the title.
- The tag block is a colon-delimited list
  surrounded by colons on both sides.
  For example, `:a:b:c:`.
- A heading with no tags has no trailing colon block at all.
- Tag characters are restricted
  to lowercase alphanumerics plus `-` and `_`.
- Tags are **inherited downward** for reporting and filtering purposes:
  a subtask inherits every tag carried by its ancestors.
  Inherited tags are computed at read time
  and are never physically duplicated in the file.

---

## 4. Task body sections

A task's description precedes its first body heading.
Subsequent updates, clocks, tasks, and events may appear in any order.
Their heading levels establish ownership as described in section 2.
Each description, update body, or clock body ends at the next heading,
regardless of that heading's level.

### 4.1 Description block

Any paragraphs and ordinary Markdown content
appearing directly after the task heading,
before the first sub-heading,
is the task's description such as its initial requirements or notes.

### 4.2 Update sections

A heading inside a task or event
that does not match a task, `EVENT`, or `CLOCK:` entry
is a freeform update in both parsing modes.
An optional datetime (section 4.5)
may appear as the first token of the heading text:

```markdown
# TODO Write the parser
### 2025-06-10T14:30+02:00 Progress update
Work continued on the tokeniser.
```

If no timestamp is present, the update simply has no recorded time.

### 4.3 Clock entries

A sub-heading of the form:

```
### CLOCK: [DATETIME]--[DATETIME] [DESCRIPTION]
```

records a closed time-tracking session.
An **open** (currently running) session
omits the second datetime but keeps the `--`:

```
### CLOCK: [DATETIME]-- [DESCRIPTION]
```

| Component | Rule |
|---|---|
| `DATETIME` | Datetime as defined in §4.5, e.g. `2025-06-10T14:30:00+02:00` or `2025-06-10T12:30:00Z`. Seconds are optional. |
| `DESCRIPTION` | Optional free text after the second timestamp (or after the lone timestamp for an open session). |

Body paragraphs beneath a `CLOCK:` heading are work notes
describing what was done during that session.

Open clocks are valid file entries, including multiple open clocks.

### 4.4 Subtask headings

Any deeper-level heading matching the task heading syntax (section 3)
is a subtask.
Subtasks recursively contain
the same body structure described in this section
including description, updates, clocks, further subtasks.

### 4.5 Datetimes and dates

The datetime grammar shared by clocks, updates, and events is:

```
DATETIME := YYYY-MM-DD "T" HH:MM [":" SS] OFFSET
OFFSET   := "Z" | ("+" | "-") HH:MM
```

Numeric fields have the displayed fixed widths.
Dates and times must be valid calendar values.
Hours use the 24-hour clock.
Fractional seconds, week dates, ordinal dates,
and a space in place of `T`
are not part of this format.
`Z` means UTC.
A signed offset expresses the difference from UTC.
Lenient mode also accepts the same datetime
without an offset (section 5).

A date alone, such as a recurrence's UNTIL date, uses `YYYY-MM-DD`
and has no timezone suffix.

---

## 5. Strict vs. lenient mode

Strict mode accepts the syntax defined here.
Lenient mode provides the following recovery rules for hand-edited files;
it does not accept arbitrary ISO 8601 forms.
Warnings are collected for the caller, rather than raised as errors.

| Rule | Strict | Lenient |
|---|---|---|
| Task status and `EVENT` keywords | Case-sensitive | Case-insensitive |
| `CLOCK:` keyword | Case-sensitive | Case-sensitive |
| Timezone in datetime | Required; error if absent | Warning; assume local system timezone |
| Open `CLOCK:` | Valid, with a warning by default | Valid, without a warning by default |
| Freeform heading inside a task or event | Update section | Update section |
| Heading without an enclosing task or event, other than a task or event itself | Error | Warning; skip heading and its body |
| Missing `--` in `CLOCK:` | Error | Best-effort recovery as an open clock; warn and skip if unrecoverable |
| Invalid recurrence rule | Error | Warning; preserve raw rule text |

Other invalid datetimes remain errors in both modes.
Recovery does not make the original file conform to the strict syntax.

---

## 6. Worked example

```markdown
# TODO Write the parser :python:core:
Parse task headings and associate their body sections.

### 2025-06-09T09:00+02:00 Kickoff
Read through the design doc and sketched the token types.

### CLOCK: [2025-06-09T09:15+02:00]--[2025-06-09T11:00+02:00] Initial scaffolding
Implemented heading recognition.

### CLOCK: [2025-06-10T09:00+02:00]-- Building the hierarchy
Associating entries with their parents.

## TODO Handle edge cases
Check skipped heading levels and tags containing digits.

# DONE Add logging :core:
Structured logging via the stdlib `logging` module.

### CLOCK: [2025-06-05T13:00+02:00]--[2025-06-05T14:30+02:00]
```

In this example, "Handle edge cases" is a subtask of "Write the parser"
and inherits the `python` and `core` tags for reporting purposes
even though it declares no tags of its own.

---

## 7. Scheduling extension: `EVENT` entries

This is an additive extension to the format.
It does not change the meaning
of any existing task, update, or clock syntax.

### 7.1 EVENT heading syntax

```
{HASHES} EVENT [DATETIME--DATETIME] {TITLE} [RECUR {RULE}] [:{TAG}:{TAG}:...]
```

| Component | Rule |
|---|---|
| `EVENT` | Literal keyword, case-sensitive in strict mode. |
| `[DATETIME--DATETIME]` | Mandatory scheduled span. Both ends required. Same datetime rules as `CLOCK:` (§4.5). |
| `{TITLE}` | Free text describing the event. |
| `RECUR {RULE}` | Optional inline recurrence rule (§7.3), placed after the title and before the tag block. |
| Tag block | Same `:tag1:tag2:` syntax as tasks. |

Example:

```markdown
## EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] Sprint planning :meeting:
## EVENT [2025-09-03T09:00+01:00--2025-09-03T11:00+01:00] Focus: parser work RECUR +1w :block:
```

### 7.2 EVENT body structure

An event may be top-level or nested inside a task or another event.
It has a description
followed by any combination of clocks, updates, and deeper events,
using the same body ownership rules as tasks (section 4).
Clocks record actual attendance or work.
The event's heading records its scheduled span.
Tasks cannot be nested inside events.
Tags are inherited from enclosing tasks and events
using the rules in section 3.1.

### 7.3 Recurrence rules

```
RULE      := PREFIX INTERVAL UNIT [WEEKDAYS] [UNTIL]
PREFIX    := "+" | "++" | ".+"
INTERVAL  := integer >= 1
UNIT      := "d" | "w" | "m" | "y"
WEEKDAYS  := weekday selector, only valid with unit "w" or "m"
UNTIL     := "@" YYYY-MM-DD
```

The prefix, interval, and unit are adjacent.
A weekday selector and an UNTIL date
are each separated from the preceding component by whitespace.
Units are lowercase.
Weekday names are uppercase `MON`, `TUE`, `WED`,
`THU`, `FRI`, `SAT`, or `SUN`.

Weekly selectors are a single weekday
or a comma-separated list without spaces (`MON,WED`).
Monthly selectors are a nonzero integer followed by a weekday:
`2MON` means the second Monday,
and `-1FRI` the last Friday.
Positive indices count from the start of the month.
Negative indices count from its end.
A selector with no matching date produces no occurrence that month.
Selectors are not valid for daily or yearly rules.

For an anchored recurrence,
the event's start supplies the initial date, time, and timezone.
Occurrences do not precede the anchor.
Calendar rules:

- Daily intervals count calendar days from the anchor.
- Weekly intervals count Monday-based weeks from the anchor's week.
  Without a selector, use the anchor's weekday.
- Monthly intervals count months from the anchor's month.
  Without a selector, use the anchor's day of the month.
- Yearly intervals count years from the anchor's year,
  using its month and day.
- Invalid calendar dates are skipped, not shifted:
  a monthly recurrence on the 31st skips months without that date,
  and a yearly recurrence on February 29 skips non-leap years.
- UNTIL is a valid calendar date and is inclusive,
- compared with each occurrence's date in the anchor's timezone.

**TODO:**
Define the distinct rescheduling behaviors of `+`, `++`, and `.+`,
including how completion or the current date affects the anchor.
Prefix-specific behavior is not yet specified.
See the README for the implementation's current behavior.

In strict mode an unrecognised rule string is a parse error,.
In lenient mode it is stored as a raw string with a warning.

---

## 8. Versioning of this document

Changes to this spec that add new syntax (such as section 7) are additive
and backward compatible.
Existing `taskmd` files remain valid.
Changes that alter the meaning of existing syntax
will bump the major version
and be called out explicitly at the top of this document.
