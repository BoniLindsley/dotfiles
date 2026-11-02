#!/usr/bin/env python3
"""Show how a file differs between two rclone locations."""

# Standard libraries.
import difflib
import enum
import typing

from typing import List, Union

# Internal modules.
from .rc import Daemon, RcError

LIMIT = 1024 * 1024
"""Files larger than this many bytes are not compared."""

CONTEXT = 3
"""Unchanged lines shown around each change."""


class Reason(enum.Enum):
    """Why a file has no lines to show."""

    SAME = "same"
    LINE_ENDINGS = "line-endings"
    BINARY = "binary"
    TOO_LARGE = "too-large"
    LEFT_MISSING = "left-missing"
    RIGHT_MISSING = "right-missing"


Line = typing.NamedTuple(
    "Line",
    [
        ("kind", str),
        ("left", Union[None, int]),
        ("right", Union[None, int]),
        ("text", str),
    ],
)
"""A line of a hunk, with its 1-based number on each side it is on.

``kind`` is ``" "`` if on both sides, ``"+"`` if only on the left
and ``"-"`` if only on the right.
"""

Diff = typing.NamedTuple(
    "Diff", [("hunks", List[List[Line]]), ("reason", Union[None, Reason])]
)
"""Changed lines with their context, or the reason none are shown."""


def diff(
    daemon: Daemon, left: str, right: str, path: str, *, limit: int = LIMIT
) -> Diff:
    """Compare file ``path`` under two rclone paths line by line.

    See `diff_contents` for how the contents compare.
    """
    left_content = _read(daemon, left, path, limit=limit)
    if left_content is None:
        return Diff(hunks=[], reason=Reason.LEFT_MISSING)
    right_content = _read(daemon, right, path, limit=limit)
    if right_content is None:
        return Diff(hunks=[], reason=Reason.RIGHT_MISSING)
    return diff_contents(left_content, right_content, limit=limit)


def diff_contents(left: bytes, right: bytes, *, limit: int = LIMIT) -> Diff:
    """Compare two file contents line by line.

    Line endings are ignored in the hunks;
    files that differ only in them are reported as such.
    """
    if len(left) > limit or len(right) > limit:
        return Diff(hunks=[], reason=Reason.TOO_LARGE)
    if left == right:
        return Diff(hunks=[], reason=Reason.SAME)
    try:
        left_lines = text_lines(left)
        right_lines = text_lines(right)
    except ValueError:
        return Diff(hunks=[], reason=Reason.BINARY)
    if left_lines == right_lines:
        return Diff(hunks=[], reason=Reason.LINE_ENDINGS)
    return Diff(hunks=hunks(left_lines, right_lines), reason=None)


def _read(
    daemon: Daemon, fs: str, path: str, *, limit: int
) -> Union[None, bytes]:
    """Read a file, or return ``None`` if missing.

    Reads one byte over ``limit``, so that a larger file can be told.
    """
    try:
        return daemon.read(fs, path, limit=limit + 1)
    except RcError as error:
        if error.status == 404:
            return None
        raise


def text_lines(content: bytes) -> List[str]:
    """Split UTF-8 text at any line ending; raise `ValueError` if binary."""
    if b"\0" in content:
        raise ValueError("Contains NUL")
    text = content.decode("utf-8")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # A final line ending ends the last line rather than starting one.
    if lines[-1] == "":
        lines.pop()
    return lines


def hunks(left: List[str], right: List[str]) -> List[List[Line]]:
    """Group changes from ``right`` to ``left`` with context lines."""
    matcher = difflib.SequenceMatcher(a=right, b=left)
    result = []  # type: List[List[Line]]
    for group in matcher.get_grouped_opcodes(CONTEXT):
        hunk = []  # type: List[Line]
        for tag, right_start, right_end, left_start, left_end in group:
            if tag == "equal":
                hunk.extend(
                    Line(
                        kind=" ",
                        left=left_start + offset + 1,
                        right=right_start + offset + 1,
                        text=left[left_start + offset],
                    )
                    for offset in range(left_end - left_start)
                )
                continue
            hunk.extend(
                Line(kind="-", left=None, right=index + 1, text=right[index])
                for index in range(right_start, right_end)
            )
            hunk.extend(
                Line(kind="+", left=index + 1, right=None, text=left[index])
                for index in range(left_start, left_end)
            )
        result.append(hunk)
    return result
