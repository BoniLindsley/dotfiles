#!/usr/bin/env python3

# Standard libraries.
import curses
import os
import signal
import typing

from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext.input_loop import _resize, keep_resize_handler

needs_sigwinch = pytest.mark.skipif(
    not hasattr(signal, "SIGWINCH"), reason="no SIGWINCH"
)


class TestResize:
    def test_resizes_to_terminal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            os, "get_terminal_size", lambda: os.terminal_size((100, 30))
        )
        resizeterm = Mock()
        monkeypatch.setattr(curses, "resizeterm", resizeterm)
        _resize()
        resizeterm.assert_called_once_with(30, 100)

    def test_without_terminal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def no_terminal() -> os.terminal_size:
            raise OSError("not a terminal")

        monkeypatch.setattr(os, "get_terminal_size", no_terminal)
        resizeterm = Mock()
        monkeypatch.setattr(curses, "resizeterm", resizeterm)
        _resize()
        resizeterm.assert_not_called()


class TestKeepResizeHandler:
    @needs_sigwinch
    def test_restores(self) -> None:
        previous = signal.getsignal(signal.SIGWINCH)
        with keep_resize_handler():
            # A Python handler, so ncurses does not install its own.
            assert callable(signal.getsignal(signal.SIGWINCH))
            os.kill(os.getpid(), signal.SIGWINCH)
        assert signal.getsignal(signal.SIGWINCH) == previous

    @needs_sigwinch
    def test_unknown_previous(self, monkeypatch: pytest.MonkeyPatch) -> None:
        handlers = []

        # Handlers installed outside Python are reported as None.
        def set_handler(signum: int, handler: typing.Any) -> None:
            assert signum == signal.SIGWINCH
            handlers.append(handler)

        monkeypatch.setattr(signal, "signal", set_handler)
        with keep_resize_handler():
            pass
        assert handlers[-1] == signal.SIG_DFL

    def test_without_sigwinch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(signal, "SIGWINCH", raising=False)
        monkeypatch.setattr(signal, "signal", Mock())
        with keep_resize_handler():
            pass
        signal.signal.assert_not_called()  # type: ignore[attr-defined]
