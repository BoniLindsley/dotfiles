# bonipy35

## Installation

Using pipenv

```sh
# Install into insolated environment.
pipenv install .

# Test installation.
pipenv run python3 -m bonipy35 logging_ext 'Hello, World!'
```

Using uv

```bash
# Creates .venv and install into it.
uv venv
uv pip install --editable '.[dev]'

uv run -m bonipy35 logging_ext 'Hello, World!'
```

## Asyncio and ncurses

See the [curses_ext documentation](src/bonipy35/curses_ext/README.md)
for event-loop usage, examples, and the mini-editor demonstration.

## Interactive Python helpers

Start Python and import the REPL helpers:

```python
from bonipy35.repl import *
git = Command("git")
git["status"] = "status --short"
process = U(git.status)
process.returncode
```

`U` waits for the command and returns its completed process; `oops` keeps
processes available through tab completion. `Command()` expands the last REPL
result, including a returned process's command arguments. Strings accept shell
quoting, but commands execute without a shell. `pip.install.user` and
`pip.uninstall` use the current Python interpreter.

Curses examples, including the tower defence game, run through
`python -m bonipy35.curses_ext tower`; see
[the curses examples](src/bonipy35/curses_ext/README.md).
