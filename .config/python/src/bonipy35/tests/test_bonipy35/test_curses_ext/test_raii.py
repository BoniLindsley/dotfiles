#!/usr/bin/env python3

# Standard libraries.
import curses

from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext.raii import initialise


class TestInitialise:
    @pytest.mark.parametrize("color", [False, True])
    def test_cleanup(
        self, window: Mock, monkeypatch: pytest.MonkeyPatch, color: bool
    ) -> None:
        monkeypatch.setattr(curses, "has_colors", lambda: color)
        with pytest.raises(ValueError):
            with initialise(initscr=lambda: window) as screen:
                assert screen is window
                raise ValueError()
        window.keypad.assert_called_with(False)
        curses.endwin.assert_called_once()  # type: ignore[attr-defined]

    def test_setup_failure(self, window: Mock) -> None:
        window.keypad.side_effect = curses.error()
        with pytest.raises(curses.error):
            with initialise():
                pass
        curses.echo.assert_called_once()  # type: ignore[attr-defined]
        curses.nocbreak.assert_called_once()  # type: ignore[attr-defined]
        curses.endwin.assert_called_once()  # type: ignore[attr-defined]
