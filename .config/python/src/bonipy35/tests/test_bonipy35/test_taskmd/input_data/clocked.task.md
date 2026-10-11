# TODO Write the parser :python:core:
Implement the two-stage scanner/builder described in the design doc.

### CLOCK: [2025-06-09T09:15:00+02:00]--[2025-06-09T11:00:00+02:00] Initial scaffolding
Set up the module layout and stub classes for model, parser, errors,
and cli.

### CLOCK: [2025-06-10T09:00:00+02:00]--[2025-06-10T12:30:00+02:00] Stage 1 scanner
Implemented the line scanner and wrote the first fixture-based unit
tests against it.

### CLOCK: [2025-06-11T09:00:00+02:00]-- Continuing stage 2
Working through the tree builder in strict mode.

# DONE Add logging :core:
Structured logging via the stdlib `logging` module.

### CLOCK: [2025-06-05T13:00:00+02:00]--[2025-06-05T14:30:00+02:00]
Wired up a `logging.basicConfig` call and a `-v` flag.

# TODO Review open sessions across the team :ops:
A task with no clock entries at all yet, to make sure the parser and
reporting tool both handle the empty-clocks case cleanly.
