#!/usr/bin/env python3

# Standard libraries.
from collections import abc
import contextlib
import curses
import logging
import sys
import typing as t


_P = t.ParamSpec("_P")

_logger = logging.getLogger(__name__)


class ScreenProtocol(t.Protocol):
    def keypad(self, yes: bool) -> None:
        ...


@contextlib.contextmanager
def initialise(
    initscr: abc.Callable[_P, ScreenProtocol]
) -> abc.Iterator[ScreenProtocol]:
    with contextlib.ExitStack() as stack:
        stdscr = initscr()
        stack.callback(curses.endwin)

        curses.noecho()
        stack.callback(curses.echo)

        curses.cbreak()
        stack.callback(curses.nocbreak)

        stdscr.keypad(True)
        stack.callback(stdscr.keypad, False)

        yield stdscr


def main(argv: None | list[str] = None) -> int:
    del argv
    logging.basicConfig(level=logging.DEBUG)
    _logger.debug("Starting.")
    with initialise(curses.initscr) as stdscr:
        del stdscr
    return 0


if __name__ == "__main__":
    sys.exit(main())
