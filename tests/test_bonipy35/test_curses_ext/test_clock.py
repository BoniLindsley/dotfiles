#!/usr/bin/env python3

# Standard libraries.
import asyncio
import curses

from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext.selector_loop import EventLoop
from bonipy35.curses_ext.clock import async_run, clock


class TestAsyncRun:
    def test_clock(self, loop: EventLoop, window: Mock) -> None:
        window.getch.side_effect = [-1, curses.KEY_RESIZE, ord("q")] + [
            -1
        ] * 20
        assert loop.run_until_complete(async_run()) == 0
        window.noutrefresh.assert_called()


class TestClock:
    def test_clock_timer_and_tiny_screen(
        self, loop: EventLoop, window: Mock
    ) -> None:
        window.getmaxyx.return_value = (1, 1)

        async def check() -> None:
            task = loop.create_task(clock(loop))
            await asyncio.sleep(0.11)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        loop.run_until_complete(check())
        assert window.noutrefresh.call_count >= 2
        assert curses.doupdate.call_count == window.noutrefresh.call_count  # type: ignore[attr-defined]
