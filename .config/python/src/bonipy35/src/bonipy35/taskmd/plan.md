# Agent Plan: `taskmd` — Markdown Task & Time-Tracking Tool

## Overview

`taskmd` is a Python project that defines a Markdown-based file format for
storing hierarchical to-do tasks with time-tracking, then provides a CLI tool
and a Vim plugin built on top of a shared library.

The project is structured into five incremental phases:

1. File format specification
2. Parser and data model
3. Reporting tool (CLI)
4. Time-tracking control (CLI)
5. Vim integration (thin Python shim over the CLI)

---

## Phase 1 — File Format Specification

Deliverable: `SPEC.md` — the canonical, versioned reference document.

### 1.1 — Top-level structure

A single `.task.md` file (or any `.md` file with a magic comment) contains one or more
task headings at any Markdown heading level. The heading level establishes the
parent-child (task-subtask) relationship.

Using `.task.md` as the extension means editors that do not know about `taskmd`
fall back gracefully to standard Markdown syntax highlighting and rendering,
since the file is valid Markdown.

```
# TODO Write the parser :python:core:
# DONE Add logging :core:
## TODO Handle edge cases
```

### 1.2 — Task heading syntax

```
{HASHES} {STATUS} {TITLE} [:{TAG}:{TAG}:...]
```

- `{HASHES}` — one or more `#` characters; depth determines nesting.
- `{STATUS}` — one of `TODO`, `DONE`, `DROP`, `WAIT` (case-sensitive in
  strict mode; case-insensitive in lenient mode).
- `{TITLE}` — free text, may not contain `:` sequences that look like a tag
  block.
- Tag block — optional, must be the last token on the heading line, of the
  form `:tag1:tag2:`. Tags are lowercase alphanumeric plus `-` and `_`.

### 1.3 — Task body sections

Immediately after the task heading, the file may contain, in order:

**Description block** — any paragraphs and normal Markdown content before the
first sub-heading. Treated as the initial task description / requirements.

**Update sections** — sub-headings whose text is _not_ a status keyword and
_not_ a `CLOCK:` line. These are freeform update entries. An optional
timestamp may appear as the first line of the update body:

```
### 2025-06-10T14:30+02:00 Progress update
Work continued on the tokeniser.
```

The timestamp is ISO 8601 with a required timezone offset when written by
`taskmd` (e.g. `+02:00` or `Z`). In strict mode a timezone-less datetime is
rejected. In lenient mode it is accepted with a warning, and the local system
timezone is assumed.

**Clock entries** — sub-headings of the form:

```
### CLOCK: [DATETIME]--[DATETIME] [DESCRIPTION]
```

or, for an open (running) session:

```
### CLOCK: [DATETIME]-- [DESCRIPTION]
```

- `DATETIME` — ISO 8601 datetime with a required timezone offset (e.g.
  `2025-06-10T14:30:00+02:00` or `2025-06-10T12:30:00Z`). Seconds are
  optional. `taskmd` always writes timestamps with an explicit offset; in
  lenient mode, a timezone-less datetime is accepted with a warning and the
  local system timezone is assumed.
- `DESCRIPTION` — optional free text on the same heading line after the
  second timestamp.
- Body paragraphs below a `CLOCK:` heading describe the work done during
  that session.

**Subtask headings** — deeper-level headings that match the task heading
syntax are subtasks. They recursively contain the same body structure.

### 1.4 — Tag format

- Tags appear only in heading lines, after the title.
- The tag block is a colon-delimited list surrounded by colons: `:a:b:c:`.
- A heading with no tags simply has no trailing colon block.
- Tags are inherited downward for reporting purposes (a subtask inherits its
  parent's tags) but are _not_ physically duplicated in the file.

### 1.5 — Strict vs. lenient mode

| Rule | Strict | Lenient |
|---|---|---|
| Status keywords | Case-sensitive | Case-insensitive |
| Datetime format | ISO 8601 only | Common formats accepted |
| Timezone in datetime | Required; error if absent | Warning + assume local tz |
| Unclosed `CLOCK:` | Warning only | Silently accepted |
| Unknown heading in task body | Error | Treated as update section |
| Missing `--` in CLOCK | Error | Best-effort parse |

### 1.6 — File identification

A `.task.md` extension is the primary signal. Alternatively, any `.md` file
beginning with the HTML comment `<!-- taskmd -->` on its first line is also
recognised. The comment is valid Markdown and invisible when rendered, so the
file degrades cleanly in any Markdown viewer.

---

## Phase 2 — Parser and Data Model

Deliverable: `taskmd/` Python package with `parser.py`, `model.py`, and
`errors.py`.

### 2.1 — Data model (`model.py`)

```
@dataclass
class ClockEntry:
    start: datetime
    end: datetime | None          # None = session still open
    description: str              # from heading line, may be empty
    work_notes: str               # body paragraphs

@dataclass
class Update:
    timestamp: datetime | None
    title: str
    body: str

@dataclass
class Task:
    level: int                    # heading depth (1 = top-level)
    status: Literal["TODO","DONE","DROP","WAIT"]
    title: str
    tags: list[str]               # own tags only; inherited computed separately
    description: str              # first body block
    updates: list[Update]
    clocks: list[ClockEntry]
    subtasks: list[Task]

    # Computed helpers
    def total_duration(self, *, recursive: bool = True) -> timedelta: ...
    def effective_tags(self, parent_tags: list[str] = []) -> list[str]: ...

@dataclass
class TaskFile:
    path: Path
    tasks: list[Task]             # top-level tasks only
```

### 2.2 — Parser (`parser.py`)

The parser operates in two stages:

**Stage 1 — Line scanner.** Reads the file line by line and emits a flat
stream of typed tokens: `HeadingToken`, `BodyLineToken`. Each `HeadingToken`
carries its depth, the raw heading text, and the line number.

**Stage 2 — Tree builder.** Consumes the token stream and applies the
following rules:

- A heading whose text matches `^(TODO|DONE|DROP|WAIT)\s+(.*)` (with tag
  extraction) opens a new `Task` node at the appropriate depth.
- A heading inside a task body matching `^CLOCK:\s+\[.*` is parsed as a
  `ClockEntry`.
- Any other heading inside a task body at a depth greater than the task's
  own depth is parsed as an `Update` (with optional leading timestamp).
- Body lines between headings are accumulated into the appropriate slot
  (description, update body, or clock work notes) by tracking parser state.

**Configuration object:**

```python
@dataclass
class ParseConfig:
    strict: bool = True
    warn_open_clocks: bool = True   # overridden to False in strict=False
    require_timezone: bool = True   # strict default; False in lenient mode
    local_timezone: tzinfo = None   # used when require_timezone=False and tz absent
    datetime_formats: list[str] = field(default_factory=lambda: [
        "%Y-%m-%dT%H:%M:%S%z",     # with seconds
        "%Y-%m-%dT%H:%M%z",        # without seconds
        # lenient mode also tries common formats via python-dateutil
    ])
```

**Entry points:**

```python
def parse_file(path: Path, config: ParseConfig = ParseConfig()) -> TaskFile: ...
def parse_string(text: str, config: ParseConfig = ParseConfig(), path: Path | None = None) -> TaskFile: ...
```

### 2.3 — Errors (`errors.py`)

```
TaskmdError(Exception)               # base
  ParseError(TaskmdError)            # unrecoverable in strict mode
  ParseWarning(TaskmdError)          # surfaced in lenient mode
  ClockFormatError(ParseError)
  StatusError(ParseError)
  TimezoneError(ParseError)          # raised in strict mode for tz-less datetimes
```

In lenient mode the parser collects `ParseWarning` instances (including
`TimezoneError` demoted to a warning) and attaches them to
`TaskFile.warnings` rather than raising.

### 2.4 — Incremental build order

1. Implement `model.py` with dataclasses and stub methods.
2. Implement the line scanner and write unit tests against small fixture files.
3. Implement the tree builder with strict mode only.
4. Add lenient mode as a second pass over the same token stream, catching
   exceptions and recording warnings.
5. Add the computed helpers (`total_duration`, `effective_tags`).
6. Achieve ≥ 90 % line coverage with `pytest`.

---

## Phase 3 — Reporting Tool (CLI)

Deliverable: `taskmd/report.py` and the `taskmd report` CLI subcommand.

### 3.1 — Filtering criteria

Filtering is applied before aggregation and is composable:

| Flag | Meaning |
|---|---|
| `--from DATE` | Only clock sessions ending on or after DATE |
| `--to DATE` | Only clock sessions starting on or before DATE |
| `--tag TAG` (repeatable) | Task or any ancestor must carry TAG |
| `--status STATUS` (repeatable) | Task status must be in the set |
| `--file FILE` | Explicit file(s) to read |
| `--dir DIR` | Recursively scan DIR for `.task.md` files |
| `--depth N` | Limit recursive directory depth |
| `--strict` / `--lenient` | Parser mode |

### 3.2 — Output format

The default output is a tree mirroring the task hierarchy:

```
report.task.md
  [TODO] Write the parser                       2h 30m
    [TODO] Handle edge cases                       45m
  [DONE] Add logging                             1h 00m
──────────────────────────────────────────────────────
Grand total                                    4h 15m
```

Each line shows the task's _own_ clock time plus all descendant clock time
(recursive total). The grand total sums only the top-level tasks to avoid
double-counting.

Optional flags:

- `--format json` — machine-readable output for scripting.
- `--format csv` — flat table with one row per task.
- `--show-sessions` — expand each task to list individual clock sessions.
- `--no-inherited-tags` — disable tag inheritance for filtering.

### 3.3 — Implementation steps

1. Build a `Filter` dataclass and a `filter_tasks(tasks, filter)` function
   that works on already-parsed `Task` trees.
2. Build an `aggregate(task_file, filter)` function returning a parallel tree
   of `(task, filtered_duration, child_nodes)` tuples.
3. Implement the tree-text renderer.
4. Implement JSON and CSV renderers.
5. Wire up the `taskmd report` CLI subcommand via `argparse` (or `click`).
6. Add integration tests using fixture `.task.md` files.

---

## Phase 4 — Time-Tracking Control (CLI)

Deliverable: `taskmd/clock.py` and the `taskmd clock` CLI subcommand.

The time-tracking commands read and write `.task.md` files in-place, preserving
all content outside the modified task.

### 4.1 — Identifying the target task

The clock commands accept a task locator:

```
taskmd clock start FILE --line LINE
taskmd clock start FILE --task-title TITLE
```

`--line LINE` is the primary interface for editor integration. The parser
records the source line number of every heading. The command walks the task
tree to find the innermost task whose heading line is ≤ `LINE` and whose body
extends past `LINE`.

### 4.2 — Subcommands

```
taskmd clock start FILE --line LINE [--note TEXT]
```
Appends a new open `CLOCK:` entry to the identified task. If `--note` is
given, it is placed as the description on the `CLOCK:` heading line.
The written timestamp always includes the local timezone offset.
Exits with a non-zero status in strict mode if the task already has an
unclosed session.

```
taskmd clock stop FILE [--line LINE] [--note TEXT] [--time DATETIME]
```
Closes the open `CLOCK:` entry in the identified task. If `--line` is
omitted and there is exactly one open session in the file, that one is
closed. If there are multiple open sessions, the tool prints them and exits
with a non-zero status, letting the caller (e.g. Vim) prompt the user.
`--time DATETIME` must include a timezone offset; if absent the local system
timezone is applied and a notice is printed.

```
taskmd clock list-open FILE
```
Lists all unclosed `CLOCK:` entries in the file, with their task paths and
start times. Output is JSON for easy consumption by scripts.

```
taskmd clock status FILE [--line LINE]
```
Returns whether the task at the given line currently has an open session.
Exit code 0 = open, 1 = closed, 2 = task not found.

### 4.3 — In-place file rewriting

The file rewriter must:

- Parse the file to locate the target heading's line range.
- Perform a surgical line-level insertion or substitution (not a full
  re-serialisation, to preserve the user's own formatting).
- Write to a `.task.md.tmp` file and atomically rename it.

### 4.4 — Implementation steps

1. Add `source_line: int` to `Task`, `ClockEntry`, and `Update` in the
   model and record it during parsing.
2. Implement `find_task_at_line(task_file, line) -> Task`.
3. Implement the surgical rewriter as a class that takes a raw list of file
   lines and a line range, and can insert or replace content within it.
4. Implement `clock_start`, `clock_stop`, `list_open_clocks`, and
   `clock_status` functions in `clock.py`.
5. Wire up the `taskmd clock` subcommand group in the CLI.
6. Write tests that start/stop clocks and re-parse the result to verify
   correctness.

---

## Phase 5 — Vim Integration

Deliverable: `vim/taskmd.vim` (Vimscript autoload + filetype plugin) and
`vim/taskmd_vim.py` (thin Python shim).

### 5.1 — Architecture

```
Vim keybinding / command
      │
      ▼
Vimscript function  (vim/taskmd.vim)
  - resolves current file path
  - reads current line number
  - calls python3 taskmd_vim.run(cmd, file, line)
      │
      ▼
Python shim  (vim/taskmd_vim.py)
  - constructs the taskmd CLI argv list
  - calls subprocess.run(["taskmd", ...])
  - formats result for vim.command() / vim.eval()
      │
      ▼
taskmd CLI  (the same binary used standalone)
```

The Python shim keeps the Vimscript thin and keeps all logic in the tested
CLI. The shim is importable so it can also be tested independently.

### 5.2 — Provided Vim commands

| Command | Action |
|---|---|
| `:TaskmdClockStart` | Start a clock for the task at the cursor line |
| `:TaskmdClockStop` | Stop the open clock for the task at the cursor (or prompt if ambiguous) |
| `:TaskmdClockStatus` | Echo whether the task at the cursor has an open session |
| `:TaskmdReport` | Open a scratch buffer with the report for the current file |
| `:TaskmdReportDir` | Open a scratch buffer with the report for the current file's directory |
| `:TaskmdListOpen` | Open a quickfix list of all unclosed sessions in the current file |

### 5.3 — Filetype detection

`vim/ftdetect/taskmd.vim`:

```vim
au BufRead,BufNewFile *.task.md set filetype=taskmd
au BufRead,BufNewFile *.md
  \ if getline(1) =~# '^<!-- taskmd -->' | set filetype=taskmd | endif
```

`taskmd` filetype inherits Markdown syntax highlighting. For `.task.md` files
opened in editors that don't know about `taskmd`, the standard `.md`
association ensures they still render as Markdown.

### 5.4 — Ambiguous stop handling

When `taskmd clock list-open` returns more than one open session, the shim
calls `vim.eval('inputlist(...)')` to present a numbered menu and then calls
`taskmd clock stop --line LINE` for the chosen session.

### 5.5 — Implementation steps

1. Write the Python shim (`taskmd_vim.py`) with one function per CLI
   subcommand. Parametrise the `taskmd` binary path so tests can point it at
   the local install.
2. Write the Vimscript autoload file. Each Vim command calls
   `python3 import taskmd_vim; taskmd_vim.run(...)`.
3. Write the filetype detection file.
4. Provide an installation section in `README.md` covering both manual
   copying and `vim-plug` / `lazy.nvim` paths.
5. Write integration tests that drive the shim directly (without Vim) and
   verify the CLI calls it would generate.

---

## Project Layout

```
taskmd/
├── SPEC.md
├── README.md
├── pyproject.toml
├── taskmd/
│   ├── __init__.py
│   ├── model.py
│   ├── parser.py
│   ├── errors.py
│   ├── report.py
│   ├── clock.py
│   └── cli.py               # argparse entry point: `taskmd` binary
├── tests/
│   ├── fixtures/            # .task.md files used as test inputs
│   ├── test_parser.py
│   ├── test_report.py
│   ├── test_clock.py
│   └── test_vim_shim.py
└── vim/
    ├── ftdetect/
    │   └── taskmd.vim
    ├── ftplugin/
    │   └── taskmd.vim       # keybindings, buffer-local commands
    ├── autoload/
    │   └── taskmd.vim       # implementation of :Taskmd* commands
    └── taskmd_vim.py        # Python shim imported by autoload plugin
```

---

## Phase 6 — Scheduling Extension

This phase extends the format spec, data model, parser, and CLI with a new
first-class entry type: `EVENT`. It is designed to be a purely additive
change; all Phase 1–5 behaviour is unaffected.

---

### 6.1 — Format Spec Extension

#### 6.1.1 — EVENT heading syntax

An `EVENT` heading follows the same grammar as task headings, replacing the
status keyword:

```
{HASHES} EVENT {SPAN} {TITLE} [RECUR {RULE}] [:{TAG}:{TAG}:...]
```

- `{HASHES}` — heading depth, same nesting rules as tasks.
- `EVENT` — the literal keyword (case-sensitive in strict mode).
- `{SPAN}` — a mandatory scheduled time span in square brackets:
  `[DATETIME--DATETIME]`. Both ends are required (events always have a
  known duration). Datetimes follow the same timezone-required ISO 8601
  rules as `CLOCK:` entries.
- `{TITLE}` — free text describing the event.
- `RECUR {RULE}` — optional inline recurrence rule (see §6.1.3). The word
  `RECUR` is a literal sentinel followed by the rule string, placed after
  the title and before the tag block.
- Tag block — same `:tag1:tag2:` format as tasks. Conventional tags used
  by the schedule CLI include `meeting`, `block`, `deadline`, and
  `holiday`, but any tag is valid.

Example entries:

```markdown
## EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] Sprint planning :meeting:

## EVENT [2025-09-03T09:00+01:00--2025-09-03T11:00+01:00] Focus: parser work RECUR +1w :block:

## EVENT [2025-09-30T00:00+01:00--2025-09-30T23:59+01:00] Q3 submission deadline RECUR ++1y :deadline:

## EVENT [2025-09-15T14:00+01:00--2025-09-15T15:00+01:00] 1-on-1 with Alice RECUR .2MON :meeting:
```

#### 6.1.2 — EVENT body structure

Immediately after the heading, an `EVENT` entry may contain:

**Description block** — paragraphs of free text (agenda, notes, links).
Treated identically to a task description block.

**CLOCK: sub-headings** — actual attendance or work spans, nested one level
deeper than the `EVENT` heading. These follow the identical `CLOCK:` syntax
defined in Phase 1. The comparison between the event's scheduled `SPAN` and
its `CLOCK:` children makes the divergence (late arrival, early finish,
overtime) explicit and machine-readable without any additional syntax.

```markdown
## EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] Sprint planning :meeting:
Agenda: velocity review, backlog grooming.

### CLOCK: [2025-09-01T10:08+01:00--2025-09-01T10:52+01:00]
Arrived late; left early to take a call.
```

**Update sub-headings** — same freeform update sections as tasks, for
post-event notes.

**Sub-events** — deeper `EVENT` headings are sub-events (e.g. an agenda
item within a meeting). They obey the same nesting logic as subtasks.

#### 6.1.3 — Recurrence rules (RECUR)

The `RECUR` rule is a short string embedded in the heading line. It is
deliberately similar to org-mode's repeat cookies but extended for
weekday patterns. The rule is consumed by the schedule expander (§6.3.2)
to generate the sequence of concrete occurrences from the anchor date in
the `SPAN`.

**Rule syntax:**

```
RULE      := PREFIX INTERVAL UNIT [WEEKDAYS] [UNTIL]
PREFIX    := "+"   -- shift from last occurrence (catch-up style)
           | "++"  -- shift from original anchor (fixed-cadence style)
           | ".+"  -- shift from today if anchor is in the past
INTERVAL  := integer ≥ 1
UNIT      := "d" | "w" | "m" | "y"
WEEKDAYS  := weekday selector (see below); only valid with unit "w" or "m"
UNTIL     := "@" ISO-8601-date  -- recurrence ends on or before this date
```

**Weekday selectors:**

| Selector | Meaning |
|---|---|
| `MON`, `TUE`, `WED`, `THU`, `FRI`, `SAT`, `SUN` | Named day(s) within the interval |
| `2MON` | Second Monday of the month (nth-weekday pattern; unit must be `m`) |
| `-1FRI` | Last Friday of the month |
| `MON,WED` | Comma-separated list (unit must be `w`) |

The weekday selector is appended directly after the unit, separated by a
space within the rule string:

```
RECUR +1w MON,WED          -- every week on Monday and Wednesday
RECUR ++1m 2MON            -- second Monday of every month (fixed anchor)
RECUR +1m -1FRI @2026-12-31 -- last Friday of each month until end of 2026
RECUR ++1y                 -- annually on the anchor date
RECUR .+1d                 -- every day, catching up from today if behind
```

**Prefix semantics** (matching org-mode):

- `+` — next occurrence is `interval × unit` after the _last completed_
  occurrence. If occurrences were skipped, they are silently lost. Use for
  tasks where catching up individually makes no sense.
- `++` — next occurrence is always `interval × unit` after the _original
  anchor_, regardless of when last completed. Use for fixed-cadence events
  (weekly standup, monthly review).
- `.+` — next occurrence is `interval × unit` after _today_. Use for
  recurring events where the exact date matters less than maintaining
  spacing from now.

In strict mode an unrecognised rule string is a parse error. In lenient
mode it is stored as a raw string with a warning.

#### 6.1.4 — Relationship between EVENT and tasks

An `EVENT` that allocates time for a specific task can reference it by
linking the task title or by co-locating the event as a sub-heading of
the task. Both patterns are valid:

```markdown
# TODO Implement the parser :core:

## EVENT [2025-09-04T13:00+01:00--2025-09-04T15:00+01:00] Focus session: parser work RECUR +1w :block:

### CLOCK: [2025-09-04T13:05+01:00--2025-09-04T14:45+01:00]
Good progress on stage 2.
```

When an `EVENT` is nested inside a task, the schedule CLI can report
allocated vs. actual time for that task, and the reporting CLI (Phase 3)
includes `CLOCK:` children of events in the task's total.

---

### 6.2 — Data Model Extension (`model.py`)

```python
@dataclass
class RecurRule:
    raw: str                        # original string, always preserved
    prefix: Literal["+", "++", ".+"]
    interval: int
    unit: Literal["d", "w", "m", "y"]
    weekdays: list[str]             # e.g. ["MON", "WED"] or ["2MON"]
    until: date | None

@dataclass
class Event:
    level: int                      # heading depth
    scheduled_start: datetime       # from SPAN
    scheduled_end: datetime
    title: str
    tags: list[str]
    recur: RecurRule | None
    description: str
    clocks: list[ClockEntry]        # actual attendance spans
    updates: list[Update]
    sub_events: list[Event]         # nested agenda items etc.
    source_line: int
```

`TaskFile` gains a parallel `events: list[Event]` field for top-level
events. Events nested inside tasks appear on `Task.events: list[Event]`
(a new field added to `Task`).

A helper method on `Event`:

```python
def occurrences(self, from_date: date, to_date: date) -> list[datetime]:
    """Expand recurrence rule into concrete start datetimes within range."""
    ...

def scheduled_duration(self) -> timedelta:
    return self.scheduled_end - self.scheduled_start

def actual_duration(self) -> timedelta:
    """Sum of all CLOCK: children."""
    return sum((c.end - c.start for c in self.clocks
                if c.end is not None), timedelta())

def divergence(self) -> timedelta:
    """actual_duration − scheduled_duration. Negative = left early."""
    return self.actual_duration() - self.scheduled_duration()
```

---

### 6.3 — Parser Extension

#### 6.3.1 — Heading recognition

The tree builder gains a new branch in Stage 2: a heading whose text
matches `^EVENT\s+\[.*--.*\]` is classified as an `Event` rather than a
`Task` or `Update`. The span, title, optional `RECUR …` clause, and tag
block are extracted by a dedicated `parse_event_heading()` function.

The recurrence rule parser lives in `recur.py` and is called from
`parse_event_heading()`. It returns a `RecurRule` or raises
`RecurParseError(ParseError)` in strict mode.

#### 6.3.2 — Recurrence expander (`recur.py`)

A pure function with no side effects:

```python
def expand(rule: RecurRule, anchor: datetime,
           from_date: date, to_date: date) -> list[datetime]:
    """
    Return all occurrence start times within [from_date, to_date].
    Does not modify the file; used by the schedule CLI for display.
    """
```

The expander is deliberately separate from the parser so it can be
tested exhaustively without file I/O.

---

### 6.4 — Schedule CLI (`taskmd schedule`)

Deliverable: `taskmd/schedule.py` and the `taskmd schedule` subcommand group.

#### 6.4.1 — `taskmd schedule show`

Displays upcoming events as a chronological agenda view, expanding
recurrences within a window:

```
taskmd schedule show [FILE|--dir DIR] [--from DATE] [--to DATE]
                     [--tag TAG]... [--status STATUS]...
                     [--format text|json|ical]
```

Default window is today through 14 days ahead. Example text output:

```
Mon 2025-09-01
  10:00–11:00  Sprint planning                          :meeting:  [+8m late, -8m short]
  13:00–15:00  Focus: parser work                       :block:

Wed 2025-09-03
  09:00–11:00  Focus: parser work (recurring)           :block:

Mon 2025-09-08
  10:00–11:00  Sprint planning (recurring)              :meeting:
```

The `[+8m late, -8m short]` annotation is derived from `Event.divergence()`
on past events that have `CLOCK:` children. Future occurrences show no
annotation. The annotation is omitted if actual matches scheduled exactly.

`--format ical` emits a valid iCalendar (`.ics`) stream, which can be
piped to a file or imported into any calendar application. Recurrence
rules are translated to `RRULE:` lines in the iCal output.

#### 6.4.2 — `taskmd schedule conflicts`

Reports scheduling overlaps within a window:

```
taskmd schedule conflicts [FILE|--dir DIR] [--from DATE] [--to DATE]
```

Output lists pairs of overlapping events with their time overlap duration.
Useful for catching double-bookings across multiple `.task.md` files.

#### 6.4.3 — `taskmd schedule summary`

Aggregates scheduled time by tag (or by task, if events are nested in
tasks) over a given period:

```
taskmd schedule summary [FILE|--dir DIR] [--from DATE] [--to DATE]
                        [--group-by tag|task|day|week]
```

Example output (`--group-by tag`):

```
Period: 2025-09-01 – 2025-09-30

  :meeting:   8 events    9h 00m scheduled    8h 14m actual   -46m total
  :block:    12 events   24h 00m scheduled   21h 30m actual   -2h 30m total
─────────────────────────────────────────────────────────────────────────
  Total      20 events   33h 00m scheduled   29h 44m actual   -3h 16m total
```

Scheduled time is the sum of `SPAN` durations (with recurrences expanded).
Actual time is the sum of `CLOCK:` children. The delta column is
`actual − scheduled`; negative means consistently finishing early or
arriving late.

---

### 6.5 — Vim Integration Extension

Three new Vim commands are added to `vim/autoload/taskmd.vim`:

| Command | Action |
|---|---|
| `:TaskmdScheduleShow` | Open a scratch buffer with the agenda for the next 14 days |
| `:TaskmdScheduleConflicts` | Open a quickfix list of scheduling conflicts in the current file |
| `:TaskmdScheduleSummary` | Open a scratch buffer with the summary for the current month |

No new shim functions are needed beyond calling the new CLI subcommands
with the current file path and sensible defaults for `--from` / `--to`.

---

### 6.6 — Updated Project Layout

New and changed entries are marked `(new)` and `(updated)`:

```
taskmd/
├── SPEC.md                          (updated)
├── taskmd/
│   ├── model.py                     (updated: Event, RecurRule, Task.events)
│   ├── parser.py                    (updated: EVENT branch in tree builder)
│   ├── errors.py                    (updated: RecurParseError)
│   ├── recur.py                     (new: RecurRule parser + expander)
│   ├── schedule.py                  (new: show / conflicts / summary logic)
│   ├── report.py                    (updated: includes event CLOCK: in task totals)
│   ├── clock.py                     (unchanged)
│   └── cli.py                       (updated: taskmd schedule subcommand group)
├── tests/
│   ├── fixtures/                    (updated: new .task.md files with EVENTs)
│   ├── test_parser.py               (updated)
│   ├── test_recur.py                (new: exhaustive recurrence expansion tests)
│   ├── test_schedule.py             (new)
│   ├── test_report.py               (updated: event clock totals)
│   ├── test_clock.py                (unchanged)
│   └── test_vim_shim.py             (updated)
└── vim/
    ├── autoload/
    │   └── taskmd.vim               (updated: three new commands)
    └── taskmd_vim.py                (updated: three new shim functions)
```

---

### 6.7 — Implementation Steps

1. Extend `model.py` with `RecurRule` and `Event`; add `Task.events`.
2. Write `recur.py`: rule parser first, then the expander. Write
   `test_recur.py` exhaustively before touching the file parser —
   the expander is pure and easy to test in isolation.
3. Extend the Stage 2 tree builder in `parser.py` to recognise `EVENT`
   headings and build `Event` objects, including nesting `CLOCK:` and
   `Update` children under them.
4. Implement `schedule.py`: `show`, `conflicts`, and `summary` functions
   operating on already-parsed `TaskFile` objects.
5. Wire up `taskmd schedule` subcommands in `cli.py`.
6. Update `report.py` so that `CLOCK:` entries nested under an `EVENT`
   that is itself nested under a `Task` are included in the task's
   `total_duration`.
7. Add the three Vim commands and shim functions.
8. Add iCal export last, as it has no dependencies on other new code.

---

## Dependency Summary

| Purpose | Library |
|---|---|
| CLI | `argparse` (stdlib) or `click` |
| Datetime parsing (lenient) | `python-dateutil` |
| Recurrence expansion | `python-dateutil` (`rrule`) for nth-weekday arithmetic |
| iCal export | `icalendar` |
| Testing | `pytest`, `pytest-cov` |
| Packaging | `pyproject.toml` with `[project.scripts]` entry point |

`python-dateutil` was already a dependency; its `rrule` module handles
the nth-weekday-of-month arithmetic that would be tedious to reimplement.
The `icalendar` library is added only for iCal export and is an optional
dependency (`pip install taskmd[ical]`).

No parser-generator library is needed; the two-stage scanner/builder is simple
enough to implement directly against the stdlib.

---

## Milestone Checklist

- [ ] Phase 1: `SPEC.md` written and reviewed
- [ ] Phase 2: Parser passes all fixture tests; ≥ 90 % coverage
- [ ] Phase 3: `taskmd report` produces correct totals on fixture files
- [ ] Phase 4: `taskmd clock start/stop` round-trips cleanly through re-parse
- [ ] Phase 5: Vim shim tested standalone; `:TaskmdClockStart` / `:TaskmdClockStop` work in a real Vim session
- [ ] Phase 6: Recurrence expander passes exhaustive tests; `taskmd schedule show` output verified against hand-calculated fixtures
