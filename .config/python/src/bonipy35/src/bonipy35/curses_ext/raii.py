#!/usr/bin/env python3

# Standard libraries.
import contextlib
import curses

from typing import Callable, Iterator, Union


@contextlib.contextmanager
def initialise(
    initscr: Union[None, Callable[[], "curses.window"]] = None,
) -> Iterator["curses.window"]:
    """Restore terminal modes even if setup or the application fails."""
    with contextlib.ExitStack() as stack:
        if initscr is None:
            initscr = curses.initscr

        stdscr = initscr()
        stack.callback(curses.endwin)

        curses.noecho()
        stack.callback(curses.echo)

        curses.cbreak()
        stack.callback(curses.nocbreak)

        stdscr.keypad(True)
        stack.callback(stdscr.keypad, False)
        if curses.has_colors():
            curses.start_color()

        yield stdscr
