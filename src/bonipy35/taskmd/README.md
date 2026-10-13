# taskmd

A Markdown-based file format for hierarchical to-do tasks
with time-tracking and scheduling,
plus a CLI and Vim plugin built on top of a shared Python library.

`taskmd` files use the `.task.md` extension
(or a `<!-- taskmd -->` marker on the first line of a `.md` file)
so they degrade gracefully to plain Markdown
in any editor that doesn't know about `taskmd`.

## Implementation

The package provides strict and lenient parsing,
hierarchical task reports, clock start/stop/status commands,
and event agendas, conflict detection,
and scheduled-versus-actual summaries.
Runtime code uses only the Python standard library
and supports Python 3.5.
Development checks
use current versions of pytest, Black, mypy, pylint, coverage, and tox.

Clock edits preserve unaffected bytes,
including mixed line endings and unterminated final lines.
Appending a heading necessarily terminates the previous line
if it lacked a newline.
Writes use a temporary file and rename.

Recurrence supports daily, weekly, monthly, and yearly intervals,
weekly weekday lists, positive and negative monthly nth weekdays,
and inclusive UNTIL dates.
Invalid calendar dates are skipped rather than shifted.
All three prefixes (`+`, `++`, `.+`) currently expand as a fixed cadence
from the event's anchor.
Completion-based rescheduling is not implemented.

The [file-format specification](SPEC.md) defines heading levels 1–6.
The parser also accepts deeper levels
for applications that need more nesting.
Heading recognition is line based, including inside Markdown code fences.
Closing heading hashes are retained as text.

Default datetime parsing accepts minutes or seconds with `T`
and an explicit timezone.
In addition to the specification's `Z` and `±HH:MM`,
clock and event timestamps accept `±HHMM` and `±HH` offsets.
Library callers can configure additional datetime formats.
Lenient mode assumes the local system timezone for timestamps
without an offset and collects a warning.

Multiple open clocks can be parsed.
In strict mode,
`clock start` refuses to add another open clock to the selected task.
Lenient mode permits it.
`clock stop` without a task selection
requires exactly one open task clock in the file.
Selecting a task closes its first open clock.

Lenient parsing preserves malformed recurrence text with a warning,
but currently supplies a daily recurrence fallback
to the scheduling layer.
Use strict parsing for scheduling when invalid rules must be rejected.

The Vim integration separates testable CLI logic
in `src/bonipy35/taskmd/vim.py`
from the embedded-editor adapter in `vim/taskmd_vim.py`.
Unit tests cover both layers.
Integration tests drive real Neovim when it is installed.
The top-level `vim/` adapter
is outside the coverage and static-check scopes configured for `src/`.

## Usage

> The examples below use `taskmd` as shorthand for brevity.
> There is no standalone `taskmd` executable yet.
> This package lives inside the `bonipy35` monorepo,
> so the real invocation
> is `python3 -m bonipy35 taskmd <command> ...`.
> For example,
> `python3 -m bonipy35 taskmd report notes.task.md` or
> `python3 -m bonipy35 taskmd clock start notes.task.md --line 12`.

```bash
# Summarize tracked time for one file
taskmd report path/to/notes.task.md

# Recursively scan a directory, filter by tag and status
taskmd report --dir ~/tasks --tag core --status TODO

# Only sessions in a date range, as JSON
taskmd report notes.task.md --from 2025-06-01 --to 2025-06-30 --format json

# Start/stop time tracking on the task at a given line
taskmd clock start notes.task.md --line 12 --note "digging into the bug"
taskmd clock stop notes.task.md --note "found it"

# Or locate by exact task title instead of line number
taskmd clock start notes.task.md --task-title "Write the parser"

# See every currently-open session across the file (as JSON)
taskmd clock list-open notes.task.md

# Check whether a specific task has an open session (0=open,1=closed,2=not found)
taskmd clock status notes.task.md --line 12
```

## Project layout

- `src/bonipy35/taskmd/`:
  model, parser, CLI, reporting, clocks, scheduling, recurrence,
  and editor-independent Vim helpers.
- `src/bonipy35/taskmd/SPEC.md`: file-format reference.
- `tests/test_bonipy35/test_taskmd/`: unit and integration tests.
- `vim/`: Vimscript plugin and embedded Python adapter.

## Installing (development)

```bash
pip install -e ".[dev]"
```

## Format at a glance

```markdown
# TODO Write the parser :python:core:
Implement the two-stage scanner/builder.

### CLOCK: [2025-06-09T09:15+02:00]--[2025-06-09T11:00+02:00] Initial scaffolding
Set up the module layout and stub classes.

## TODO Handle edge cases
```

See `SPEC.md` for the complete grammar, including update sections,
strict vs. lenient parsing, tag inheritance, and the `EVENT`
scheduling extension.

## Vim plugin

`vim/` contains a Vim plugin built on top of the CLI:

```
vim/
├── ftdetect/
│   └── taskmd.vim       # *.task.md, or .md w/ <!-- taskmd --> on line 1
├── ftplugin/
│   └── taskmd.vim       # :Taskmd* commands + default keybindings
├── syntax/
│   └── taskmd.vim       # inherits Markdown highlighting
├── autoload/
│   └── taskmd.vim       # thin wrappers, call into taskmd_vim.py
└── taskmd_vim.py         # thin `import vim` adapter layer, see below
```

The logic this plugin drives
(building `taskmd` CLI argv, running it, parsing its output,
the ambiguous-stop-session flow)
actually lives in `src/bonipy35/taskmd/vim.py`
(part of the `bonipy35` package,
so it gets 100% coverage,  mypy, pylint, black enforcement).
`vim/ taskmd_vim.py` is a thin, `import vim`-requiring adapter
on top of it that is tested with a fake `vim` host and,
when available, real Neovim.

Requires Vim (or Neovim) compiled with `+python3`.

### Commands

| Command | Action |
|---|---|
| `:TaskmdClockStart` | Start a clock for the task at the cursor line |
| `:TaskmdClockStop` | Stop the open clock for the task at the cursor (prompts via `inputlist()` if more than one session is open in the file) |
| `:TaskmdClockStatus` | Echo whether the task at the cursor has an open session |
| `:TaskmdReport` | Open a scratch buffer with the report for the current file |
| `:TaskmdReportDir` | Open a scratch buffer with the report for the current file's directory |
| `:TaskmdListOpen` | Open a quickfix list of all unclosed sessions in the current file |
| `:TaskmdScheduleShow` | Show the event agenda |
| `:TaskmdScheduleConflicts` | Show scheduling conflicts |
| `:TaskmdScheduleSummary` | Summarize scheduled and actual time |

Default buffer-local keybindings (`<LocalLeader>` prefixed) are set up
in `ftplugin/taskmd.vim`; set `let g:taskmd_no_mappings = 1` before
the plugin loads to skip them and define your own.

### Installing

**Manual:**
copy (or symlink) the contents of `vim/` into your `~/.vim`
(or `~/.config/nvim` on Neovim),
preserving the `ftdetect/`, `ftplugin/`, `syntax/`
and `autoload/` subdirectories.
For example,

```bash
cp -r vim/* ~/.vim/
```

**[vim-plug](https://github.com/junegunn/vim-plug):**

```vim
Plug 'file:///absolute/path/to/taskmd_project', {'rtp': 'vim'}
```

(swap the `file://` URL for a real git remote if this repo is
published somewhere; `rtp` points plug at the `vim/` subdirectory
since this isn't a standalone plugin repo).

**[lazy.nvim](https://github.com/folke/lazy.nvim):**

```lua
{
  dir = "/absolute/path/to/taskmd_project",
  name = "taskmd",
  config = function()
    vim.opt.rtp:append("/absolute/path/to/taskmd_project/vim")
  end,
}
```

### How it works

Vimscript (`autoload/taskmd.vim`)
resolves the current buffer's file path and cursor line,
then hands off to `taskmd_vim.py` (in `vim/`),
which delegates to `bonipy35.taskmd.vim` (in `src/`)
to build the equivalent `taskmd` CLI invocation,
run it as a subprocess,
and parse the result.
The thin `vim/taskmd_vim.py` layer
then formats that result back into the buffer, quickfix list or echo area
via the `vim` module.

The split is deliberate.
Everything worth unit-testing
(argv construction, output parsing, the ambiguous-stop-session flow)
lives in plain, `vim`-import-free Python in `src/bonipy35/taskmd/vim.py`,
covered by `tests/test_bonipy35/test_taskmd/test_vim.py`
without needing a running Vim instance,
and subject to the same 100%-coverage, mypy, pylint, black gates
as the rest of the package.
Only the adapter functions
in `vim/taskmd_vim.py` (`vim_clock_start`, `vim_clock_stop`, etc.)
touch the `vim` module directly.
`test_vim_shim.py` exercises that adapter with a fake host,
while `test_vim_integration.py` drives the real plugin
when Neovim is available.
`stubs/vim.pyi` supplies type declarations for development tools.
It has no runtime behavior.

When report or schedule receives no files or `--dir`, it recursively scans
`$XDG_DATA_HOME/bonipy35/taskmd` (default: `~/.local/share/bonipy35/taskmd`).
Explicit inputs override this default. Reading does not create the directory.
