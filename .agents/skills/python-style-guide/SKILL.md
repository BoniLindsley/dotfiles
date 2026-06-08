---
name: python-style-guide
description: General rules for coding Python
---

# Python Type Hints

## Version Compatibility

Make type hints compatible with Python 3.5 at runtime when possible
to make supporting Debian 9 easier.
In particular, expect tooling environment to be at the latest.

## Referring to Enclosing Class

When adding Python type hints, always use `"typing.Self"` as a string
instead of `"ClassType"`, `ClassType` or `typing.Self` directly
to support older Python versions.

- Using `"ClassType"` or `ClassType` makes code reuse more difficult.
- Using `typing.Self` requires Python 3.11.
- Using `"typing.Self"` is valid at runtime for Python 3.5
  and treated as `typing.Self` by modern and recent type checkers.

Example:

```python
import typing
class DataProcessor:
    def chain(self) -> "typing.Self":
        return self
```

## Use typing Module Aliases for Generics

Use `typing.Dict[str, int]`, `typing.List[str]`
instead of `dict[str, int]` and `list[str]`.
Similarly for other types such as `Set`, `Tuple`, etc.
This is to support older Python versions.

Example:

```python
from typing import Dict, List, Type

def function(numbers: List[str]) -> Dict[str, int]:
    return {key: 1 for key in numbers}
```

## Use Union instead of Optional and Pipe

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
