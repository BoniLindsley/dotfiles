#!/usr/bin/env python3

# Standard libraries.
import inspect
import pathlib
import typing


def get_module_directory(source: typing.Callable[..., typing.Any]) -> pathlib.Path:
    """
    Usage: `get_module_directory(lambda: None)`
    """
    as_string = inspect.getsourcefile(source)
    if as_string:
        return pathlib.Path(as_string).parent
    return pathlib.Path()
