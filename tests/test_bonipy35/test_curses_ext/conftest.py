#!/usr/bin/env python3

# TODO(T-032): the loop fixture repeats the EventLoop tests' one.
# pylint: disable=duplicate-code

# Standard libraries.
import asyncio
import curses
import itertools
import typing

from typing import Callable, Iterator, List
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext.input_loop import EventLoop, InputSelector


@pytest.fixture(name="window")
def fixture_window(
    monkeypatch: pytest.MonkeyPatch, selectable_stdin: None
) -> Mock:
    del selectable_stdin
    window = Mock()
    window.getch.return_value = -1
    window.getmaxyx.return_value = (24, 80)
    for name in (
        "noecho",
        "echo",
        "cbreak",
        "nocbreak",
        "endwin",
        "start_color",
        "doupdate",
    ):
        monkeypatch.setattr(curses, name, Mock())
    monkeypatch.setattr(curses, "initscr", Mock(return_value=window))
    monkeypatch.setattr(curses, "isendwin", Mock(return_value=False))
    monkeypatch.setattr(curses, "has_colors", Mock(return_value=True))

    def ungetch(key: int) -> None:
        # Curses returns a pushed back key before any other.
        rest = window.getch.side_effect
        if rest is None:
            rest = itertools.repeat(window.getch.return_value)
        window.getch.side_effect = itertools.chain([key], rest)

    monkeypatch.setattr(curses, "ungetch", ungetch)
    return window


_Loop = typing.TypeVar("_Loop", bound=asyncio.AbstractEventLoop)


@pytest.fixture(name="current_loop")
def fixture_current_loop() -> Iterator[Callable[[_Loop], _Loop]]:
    """Return a function setting a loop as current until the test ends.

    The loops are closed then.
    """
    loops = []  # type: List[asyncio.AbstractEventLoop]

    def set_current(loop: _Loop) -> _Loop:
        loops.append(loop)
        asyncio.set_event_loop(loop)
        return loop

    try:
        yield set_current
    finally:
        asyncio.set_event_loop(None)
        for loop in loops:
            loop.close()


@pytest.fixture(name="loop")
def fixture_loop(
    window: Mock, current_loop: Callable[[EventLoop], EventLoop]
) -> EventLoop:
    return current_loop(EventLoop(InputSelector(window=window)))
