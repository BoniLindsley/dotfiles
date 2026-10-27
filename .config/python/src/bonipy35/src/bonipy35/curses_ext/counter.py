#!/usr/bin/env python3
"""Persistent counter example using asyncio and ncurses."""

# Standard libraries.
import argparse
import asyncio
import datetime
import json
import pathlib
import sys
import typing

from typing import List, Union

# Internal modules.
from . import selector_loop
from . import ui


class Data:
    def __init__(self) -> None:
        self.updated_at = datetime.datetime.now()
        self.zenny = 0

    @classmethod
    def load(cls, path: pathlib.Path) -> "typing.Self":
        data = cls()
        try:
            with path.open(encoding="utf-8") as file:
                values = json.load(file)
        except FileNotFoundError:
            return data
        data.zenny = int(values["zenny"])
        timestamp = values["updated_at"]
        # Accept old saves both with and without fractional seconds.
        pattern = "%Y-%m-%dT%H:%M:%S"
        if "." in timestamp:
            pattern += ".%f"
        data.updated_at = datetime.datetime.strptime(timestamp, pattern)
        return data

    def save(self, path: pathlib.Path) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "zenny": self.zenny,
                    "updated_at": self.updated_at.isoformat(),
                },
                file,
            )


async def async_run() -> int:
    loop = typing.cast(selector_loop.EventLoop, asyncio.get_event_loop())
    path = pathlib.Path("data.json")
    data = Data.load(path)
    while True:
        ui.draw(
            loop,
            [
                "Counter: + adds, s saves, q saves and quits",
                "Zenny: " + str(data.zenny),
            ],
        )
        key = await loop.getch()
        if key == ord("+"):
            data.zenny += 1
            data.updated_at = datetime.datetime.now()
        elif key in (ord("s"), ord("q")):
            data.save(path)
            if key == ord("q"):
                return 0


def main(argv: Union[None, List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Persistent counter using asyncio and ncurses"
    )
    parser.parse_args(None if argv is None else argv[1:])
    return selector_loop.run(async_run())


if __name__ == "__main__":
    sys.exit(main())
