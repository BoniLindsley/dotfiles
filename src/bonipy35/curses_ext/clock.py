#!/usr/bin/env python3
"""Live clock: timers keep running while awaiting ncurses input."""

# Standard libraries.
import argparse
import asyncio
import datetime
import sys
import typing

from typing import List, Union

# Internal modules.
from .selector_loop import EventLoop, run
from .ui import draw


async def clock(loop: EventLoop) -> None:
    while True:
        draw(
            loop,
            [
                "Asyncio + ncurses (q to quit)",
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ],
        )
        await asyncio.sleep(0.1)


async def async_run() -> int:
    loop = typing.cast(EventLoop, asyncio.get_event_loop())
    ticker = loop.create_task(clock(loop))
    try:
        while await loop.getch() != ord("q"):
            pass
    finally:
        ticker.cancel()
        await asyncio.gather(ticker, return_exceptions=True)
    return 0


def main(argv: Union[None, List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Live clock using asyncio and ncurses"
    )
    parser.parse_args(None if argv is None else argv[1:])
    return run(async_run())


if __name__ == "__main__":
    sys.exit(main())
