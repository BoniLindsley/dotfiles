#!/usr/bin/env python3
"""Curses input through asyncio, without polling."""

# Standard libraries.
import contextlib
import curses
import os
import signal
import typing

from typing import Iterator


def _resize() -> None:
    """Resize curses to the terminal, queueing `KEY_RESIZE` on a change."""
    try:
        columns, lines = os.get_terminal_size()
    except OSError:
        return
    curses.resizeterm(lines, columns)


def _ignore_signal(signum: int, frame: typing.Any) -> None:
    del signum, frame


@contextlib.contextmanager
def keep_resize_handler() -> Iterator[None]:
    """Hold a Python SIGWINCH handler while curses is initialised.

    Ncurses then leaves SIGWINCH to the loop,
    and the previous handler is restored afterwards.
    """
    if not hasattr(signal, "SIGWINCH"):
        yield
        return
    previous = signal.signal(signal.SIGWINCH, _ignore_signal)
    try:
        yield
    finally:
        # Python cannot restore a handler installed outside it.
        signal.signal(
            signal.SIGWINCH,
            signal.SIG_DFL if previous is None else previous,
        )
