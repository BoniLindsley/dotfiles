# TODO Ship taskmd v0.1 :release:
Top-level umbrella task tracking the whole v0.1 milestone.

## TODO Write the parser :python:core:
Implement the two-stage scanner/builder described in the design doc.
Inherits the `release` tag from its parent for reporting purposes.

### TODO Handle edge cases
Multi-line titles, tags containing digits, empty tag blocks, and CRLF
line endings.

### CLOCK: [2025-06-09T09:15:00+02:00]--[2025-06-09T11:00:00+02:00] Initial scaffolding
Set up the module layout and stub classes.

## DONE Add logging :core:
Structured logging via the stdlib `logging` module.

## TODO Write documentation :docs:
Covers SPEC.md, README.md, and docstrings across the package.

### TODO Document the CLI
Man-page style `--help` text for every subcommand.

### TODO Document the file format
Point readers at SPEC.md and add a short "getting started" example.

#### DROP Add a video walkthrough
Decided against this for v0.1 — text docs are enough for the first
release, revisit for v0.2 if requested.

# TODO Plan v0.2 :planning:
A second top-level task, sibling to "Ship taskmd v0.1", with no
subtasks yet.
