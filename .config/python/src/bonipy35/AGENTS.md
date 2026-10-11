# AGENTS.md

## Commands

Create/use a working virtual environment:

- `uv venv`
- `uv pip install --editable '.[dev]'`
- `source .venv/bin/activate`

Then:

- Full validation: `python -m tox`
- Tests: `python -m pytest -q`
- One module: `python -m pytest -q tests/test_bonipy35/test_argparse_ext.py`
- Coverage: `python -m coverage run` then `python -m coverage report`

## Rules

- Keep runtime code compatible with Python 3.5; use current development tools.
- Do not use periodic polling for event-loop handling. Socket readiness support
  may be dropped when necessary to meet this requirement.
- Group tests by function in classes, use typed pytest fixtures,
  and import functions under test directly.
- Prefer temporary directories and real filesystem assertions
  for filesystem tests.
- Prefer explicit keyword arguments over dictionary expansion in function
  calls to make type errors more explicit. Dictionary expansion is fine
  when alternatives reduce readability or maintainability.
- Run full tox checks before completing code changes;
  report any checks that cannot run.

## Maintenance

Update commands when they change. Propose substantive rule changes
for user review before writing them.
