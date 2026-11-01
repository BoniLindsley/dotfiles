#!/usr/bin/env python3

# TODO(T-032): the loop fixture repeats the EventLoop tests' one.
# pylint: disable=duplicate-code

# Standard libraries.
import asyncio
import contextlib
import curses
import itertools

from typing import Iterator
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


@pytest.fixture(name="loop")
def fixture_loop(window: Mock) -> Iterator[EventLoop]:
    with contextlib.closing(EventLoop(InputSelector(window=window))) as loop:
        asyncio.set_event_loop(loop)
        try:
            yield loop
        finally:
            asyncio.set_event_loop(None)
