# TODO Write the parser :python:core:
Implement the two-stage scanner/builder described in the design doc.
Should handle strict and lenient modes.

# DONE Add logging :core:
Structured logging via the stdlib `logging` module. Wired up in
`cli.py` so verbosity can be controlled with `-v`.

# WAIT Get design sign-off :docs:
Waiting on review from the team before finalising SPEC.md.

### 2025-06-11T09:00+02:00 Sent for review
Shared SPEC.md with the team on Slack, asked for comments by Friday.

# DROP Support YAML front-matter :parser:
Decided against this — adds complexity without a clear use case, and
tags already cover most of what front-matter would have been used for.
