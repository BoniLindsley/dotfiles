#!/usr/bin/env python3
"""Compare the files of two rclone locations through ``rclone rcd``."""

# Standard libraries.
import datetime
import enum
import re
import typing

from typing import Dict, List, Union

# Internal modules.
from .rc import Daemon, RcError

_LIST = "operations/list"
_CHECK = "operations/check"

# RFC 3339 as rclone writes it, with up to nanoseconds.
_TIME = re.compile(
    r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\.(\d+))?"
    r"(?:(Z)|([+-])(\d\d):(\d\d))$"
)


class State(enum.Enum):
    """How a file compares, with the marker ``rclone check`` uses."""

    SAME = "="
    DIFFERENT = "*"
    LEFT_ONLY = "+"
    RIGHT_ONLY = "-"
    ERROR = "!"


Side = typing.NamedTuple(
    "Side", [("size", int), ("modified", datetime.datetime)]
)
"""A file as listed on one side. ``size`` is -1 if the backend cannot tell."""

Entry = typing.NamedTuple(
    "Entry",
    [
        ("path", str),
        ("state", State),
        ("left", Union[None, Side]),
        ("right", Union[None, Side]),
    ],
)
"""One file of a comparison. A side is ``None`` if it was not listed there."""


def compare(daemon: Daemon, left: str, right: str) -> List[Entry]:
    """Compare two rclone paths, such as ``remote:dir`` or a local directory.

    Returns one entry per file, sorted by path.
    A path that does not exist compares as an empty directory.
    Content equality is decided by ``operations/check``,
    using hashes where both sides support a common one.
    """
    left_files = list_files(daemon, left)
    right_files = list_files(daemon, right)
    result = daemon.call(
        _CHECK, {"srcFs": left, "dstFs": right, "combined": True}
    )
    entries = []  # type: List[Entry]
    for line in _strings(result.get("combined"), path=_CHECK):
        marker, _, name = line.partition(" ")
        try:
            state = State(marker)
        except ValueError:
            raise RcError(
                "Unexpected check line: {!r}".format(line),
                path=_CHECK,
                status=200,
            ) from None
        entries.append(
            Entry(
                path=name,
                state=state,
                left=left_files.get(name),
                right=right_files.get(name),
            )
        )
    entries.sort(key=lambda entry: entry.path)
    return entries


def list_files(daemon: Daemon, fs: str) -> Dict[str, Side]:
    """List files under ``fs`` recursively, by path relative to it.

    A path that does not exist lists as empty.
    """
    try:
        result = daemon.call(
            _LIST,
            {
                "fs": fs,
                "remote": "",
                "opt": {"recurse": True, "filesOnly": True},
            },
        )
    except RcError as error:
        if error.status == 404:
            return {}
        raise
    items = result.get("list")
    if not isinstance(items, list):
        raise _unexpected(result)
    files = {}  # type: Dict[str, Side]
    for item in items:
        if not isinstance(item, dict):
            raise _unexpected(item)
        path = item.get("Path")
        size = item.get("Size")
        modified = item.get("ModTime")
        if (
            not isinstance(path, str)
            or not isinstance(size, int)
            or not isinstance(modified, str)
        ):
            raise _unexpected(item)
        try:
            files[path] = Side(size=size, modified=parse_time(modified))
        except ValueError:
            raise _unexpected(item) from None
    return files


def parse_time(text: str) -> datetime.datetime:
    """Parse an rclone time, truncating to microseconds."""
    match = _TIME.match(text)
    if match is None:
        raise ValueError("Not an RFC 3339 time: {!r}".format(text))
    (
        year,
        month,
        day,
        hour,
        minute,
        second,
        fraction,
        utc,
        sign,
        offset_hours,
        offset_minutes,
    ) = match.groups()
    if utc:
        timezone = datetime.timezone.utc
    else:
        offset = datetime.timedelta(
            hours=int(offset_hours), minutes=int(offset_minutes)
        )
        timezone = datetime.timezone(-offset if sign == "-" else offset)
    return datetime.datetime(
        int(year),
        int(month),
        int(day),
        int(hour),
        int(minute),
        int(second),
        int((fraction or "0")[:6].ljust(6, "0")),
        tzinfo=timezone,
    )


def _strings(value: object, *, path: str) -> List[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise RcError(
            "Unexpected response: {!r}".format(value), path=path, status=200
        )
    return typing.cast(List[str], value)


def _unexpected(value: object) -> RcError:
    return RcError(
        "Unexpected response: {!r}".format(value), path=_LIST, status=200
    )
