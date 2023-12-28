# /usr/bin/env python3

# Standard libraries.
import collections.abc as cabc
import contextlib
import curses


@contextlib.contextmanager
def initialise(
    initscr: None | cabc.Callable[[], curses.window] = None
) -> cabc.Iterator[curses.window]:
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

        curses.start_color()

        yield stdscr
