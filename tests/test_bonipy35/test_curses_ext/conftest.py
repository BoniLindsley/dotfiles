#!/usr/bin/env python3

# Standard libraries.
import curses

from typing import Iterator
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext.asyncio_loop import EventLoop, use_event_loop_policy


@pytest.fixture(name="window")
def fixture_window(monkeypatch: pytest.MonkeyPatch) -> Mock:
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
        "ungetch",
    ):
        monkeypatch.setattr(curses, name, Mock())
    monkeypatch.setattr(curses, "initscr", Mock(return_value=window))
    monkeypatch.setattr(curses, "has_colors", Mock(return_value=True))
    return window


@pytest.fixture(name="loop")
def fixture_loop(window: Mock) -> Iterator[EventLoop]:
    with use_event_loop_policy(window) as policy:
        loop = policy.new_event_loop()
        policy.set_event_loop(loop)
        try:
            yield loop
        finally:
            loop.close()
