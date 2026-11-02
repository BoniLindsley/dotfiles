#!/usr/bin/env python3
"""Live clock: timers keep running while awaiting ncurses input."""

# Standard libraries.
import argparse
import asyncio
import curses
import datetime
import sys

from typing import List, Union

# Internal modules.
from .input_loop import WindowInput, run
from .ui import draw


async def clock(window: "curses.window") -> None:
    while True:
        draw(
            window,
            [
                "Asyncio + ncurses (q to quit)",
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ],
        )
        await asyncio.sleep(0.1)


async def async_run(window: "curses.window") -> int:
    window_input = WindowInput(window)
    ticker = asyncio.ensure_future(clock(window))
    try:
        while await window_input.getch() != ord("q"):
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
    return run(async_run)


if __name__ == "__main__":
    sys.exit(main())
