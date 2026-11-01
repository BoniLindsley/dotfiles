#!/usr/bin/env python3
"""Shared drawing helpers for ncurses examples."""

# Standard libraries.
import curses

from typing import List


def draw(window: "curses.window", lines: List[str]) -> None:
    window.erase()
    height, width = window.getmaxyx()
    for row, text in enumerate(lines[:height]):
        # Leave the final column free to avoid the bottom-right error.
        window.addnstr(row, 0, text, max(0, width - 1))
    window.noutrefresh()
    curses.doupdate()
