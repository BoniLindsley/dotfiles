#!/usr/bin/env python3
"""Copy picked files between two rclone locations through ``rclone rcd``."""

# Standard libraries.
import enum
import typing

from typing import Generator, Iterable, Union

# Internal modules.
from .rc import Daemon, RcError

_COPYFILE = "operations/copyfile"


class Direction(enum.Enum):
    LEFT_TO_RIGHT = "left-to-right"
    RIGHT_TO_LEFT = "right-to-left"


Result = typing.NamedTuple(
    "Result", [("path", str), ("error", Union[None, str])]
)
"""The outcome of copying one file. ``error`` is ``None`` on success."""


def copy_files(
    daemon: Daemon,
    left: str,
    right: str,
    paths: Iterable[str],
    *,
    direction: Direction
) -> Generator[Result, None, None]:
    """Copy each path, relative to both locations, in one direction.

    Yields a result as each file finishes, in the order given,
    so that callers can report progress or stop between files.
    A failed file does not stop the others.
    Files not given are left untouched; nothing is deleted.
    """
    if direction is Direction.LEFT_TO_RIGHT:
        source, destination = left, right
    else:
        source, destination = right, left
    for path in paths:
        try:
            daemon.call(
                _COPYFILE,
                {
                    "srcFs": source,
                    "srcRemote": path,
                    "dstFs": destination,
                    "dstRemote": path,
                },
            )
        except RcError as error:
            yield Result(path=path, error=str(error))
        else:
            yield Result(path=path, error=None)
