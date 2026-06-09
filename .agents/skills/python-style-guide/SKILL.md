---
name: python-style-guide
description: >
  Describes personal preferred Python coding style
  for Python code generation, modification and review tasks.
---

This skill is passive, to be applied in future requests,
and no immeidate action is expected from loaded.

# Compatibility with Older Python Versions

Make modules compatible with Python 3.5 at runtime when possible
unless an alternative minimum version is specified.
This is to make supporting Debian 9 easier,
despite its end of life status.
Debian 9 support at run time by default
is a deliberate production requirement.

For development, expect tooling environment, such as linters,
to be at the latest version.

# Module Structure and Order

- Start with standard shebang compatible with Debian.
- Optional module docstrings. Currently no guidance on its style.
- Tool configuration overrides.
- Imports.
- Implementation level logger and type hint variables.
- Module implementations.
- A `run` function as an entry point for other modules if appropriate.
- A `main` function parsing command line arguments to forward to `run`.
- Script scaffolding to run `main`.

Example:

```python
#!/usr/bin/env python3

# Need Python 3.5 support.
# pylint: disable=consider-using-f-string

# Standard libraries.
import argparse
import logging
import sys
import typing

from typing import List, Union

_logger = logging.getLogger(__name__)

_T = typing.TypeVar("_T")


def run(name: str) -> int:
    _logger.debug("Received %s", name)
    print(name)
    return 0


def main(argv: Union[None, List[str]] = None) -> int:
    """Parse command line arguments and call `run`.

    Defaults to `sys.argv` which includes the script name at `[0]`
    for use by implementation if necessary.
    """
    if argv is None:
        argv = sys.argv

    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("name")
    arguments = argument_parser.parse_args(argv[1:])

    return run(arguments.name)


if __name__ == "__main__":
    sys.exit(main())
```

# Order Imports by Standard Libraries, then Externals, Lastly Internals

- Start each of the three sections with comment headings.
- Within each heading, import modules such as `import os`
  before identifiers such as `from typing import List`.
- Within each of those, sort the lines alphabetically.
- Within identifier imports, also import alphabetically.

Example:

```python
# Standard libraries.
import os
import sys
import unittest

from typing import List, Union

# External dependencies.
import pytest

# Internal modules.
from . import utils
```

# Prefer Module Import without Identifier unless Deprecated by Built-ins

Import modules and then reference with `module.identifier`
instead of using `from module import identifier`.

- This is to make mocking easier when unit testing.
- Use alias such as `import numpy as np` if used commonly by convention.

An exception to this is when the identifier is deprecated
by a builtin or language feature that will not require an import.
This mainly applies to deprecated identifiers in the `typing` module.

- This means using `Dict[str, int]`, `List[str]` after importing them
  instead of `dict[str, int]` and `list[str]`.
- Similarly for other types such as `Set`, `Tuple`, etc.
- This is to support older Python versions,
  and easier replacements when support can be dropped.

Example:

```python
from typing import Dict, List, Type

def function(numbers: List[str]) -> Dict[str, int]:
    return {key: 1 for key in numbers}
```

# Referring to Enclosing Class

When adding Python type hints, always use `"typing.Self"` as a string
instead of `"ClassType"`, `ClassType` or `typing.Self` directly
to support older Python versions.

- Using `"ClassType"` or `ClassType` makes code reuse more difficult.
- Using `typing.Self` requires Python 3.11.
- Using `"typing.Self"` is valid at runtime for Python 3.5
  and treated as `typing.Self` by modern type checkers
  such as `mypy` and `pylint` in their recent versions.

Example:

```python
import typing

class DataProcessor:
    def chain(self) -> "typing.Self":
        return self
```

# Use Union instead of Optional and Pipe

Use `Union[None, int]` instead of `Optional[int]` and `None | int`.

- This is to make adding more supported types to `Union` easier.
- Using pipe requires Python 3.10.
- Use `None` as the first argument to make it more visible,
  especially when used with a parameter.

Example:

```python
from typing import Union

def function(number: Union[None, int] = None) -> int:
    return number or 0
```
