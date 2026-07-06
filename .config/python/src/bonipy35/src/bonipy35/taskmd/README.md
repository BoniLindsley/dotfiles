# taskmd

A Markdown-based file format for hierarchical to-do tasks with
time-tracking and scheduling, plus a CLI and Vim plugin built on top of
a shared Python library.

`taskmd` files use the `.task.md` extension (or a `<!-- taskmd -->`
marker on the first line of a `.md` file) so they degrade gracefully to
plain Markdown in any editor that doesn't know about `taskmd`.

## Status

`SPEC.md` defines the file format. The Python package implements:

- **Phase 2 (parser/model):** `model.py`, `parser.py`, `errors.py` --
  full two-stage parser (line scanner + tree builder), strict and
  lenient modes, 100% test coverage.
- **Phase 3 (reporting):** `report.py` and the `taskmd report` CLI
  subcommand -- filtering by tag/status/date range, tree/JSON/CSV
  output, multi-file and directory scanning, 100% test coverage.

Not yet implemented: `taskmd clock` (Phase 4), Vim integration
(Phase 5), and the `EVENT` scheduling extension (`taskmd schedule`,
Phase 6).

## Usage

```bash
# Summarize tracked time for one file
taskmd report path/to/notes.task.md

# Recursively scan a directory, filter by tag and status
taskmd report --dir ~/tasks --tag core --status TODO

# Only sessions in a date range, as JSON
taskmd report notes.task.md --from 2025-06-01 --to 2025-06-30 --format json
```

## Project layout

```
taskmd/
├── SPEC.md              # canonical file format specification
├── pyproject.toml
├── taskmd/               # Python package
│   ├── __init__.py
│   ├── model.py          # data model (stub)
│   ├── parser.py         # two-stage line scanner + tree builder (stub)
│   ├── errors.py         # exception hierarchy (stub)
│   └── cli.py            # `taskmd` entry point (stub)
└── tests/
    └── fixtures/          # example .task.md files used in tests
        ├── basic.task.md
        ├── clocked.task.md
        └── nested.task.md
```

## Installing (development)

```bash
pip install -e ".[dev]"
```

## Format at a glance

```markdown
# TODO Write the parser :python:core:
Implement the two-stage scanner/builder.

### CLOCK: [2025-06-09T09:15+02:00--2025-06-09T11:00+02:00] Initial scaffolding
Set up the module layout and stub classes.

## TODO Handle edge cases
```

See `SPEC.md` for the complete grammar, including update sections,
strict vs. lenient parsing, tag inheritance, and the `EVENT`
scheduling extension.
