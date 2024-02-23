#!/usr/bin/env python3

# Standard libraries.
import datetime
import io
import sys
import typing as _t

# External dependencies.
import pydantic

# Internal modules.
from .result import Ok, Result


class Title(pydantic.BaseModel):
    completed: bool = False
    priority: str = ""
    completion_date: None | datetime.datetime = None
    creation_date: None | datetime.datetime = None
    description: str = ""


class Entry(pydantic.BaseModel):
    title: Title
    content: list[_t.Union["Entry", str]]


def parse_completed(source: io.IOBase) -> bool:
    assert source.seekable(), "Todo source stream must be seekable."
    offset = source.tell()

    buffer = source.readline(2)
    completed = buffer == b"x "

    if not completed:
        source.seek(offset)
    return completed


def parse(source: io.IOBase) -> Result[Entry, str]:
    completed = parse_completed(source)
    entry = Entry(title=Title(completed=completed), content=[])
    return Ok(entry)


def main() -> int:
    return 0


if __name__ == "__main__":
    sys.exit(main())
