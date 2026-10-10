#!/usr/bin/env python3

# External dependencies.
import pytest

# Internal modules.
from bonipy35.contextlib_ext import suppress_keyboard_interrupt


class TestSuppressKeyboardInterrupt:
    def test_propagates_other_errors(self) -> None:
        with pytest.raises(ValueError, match="failure"):
            with suppress_keyboard_interrupt():
                raise ValueError("failure")

    def test_runs_body(self, capsys: pytest.CaptureFixture[str]) -> None:
        with suppress_keyboard_interrupt():
            print("body")
        assert capsys.readouterr().out == "body\n"

    def test_suppresses_interrupt_and_clears_line(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with suppress_keyboard_interrupt():
            raise KeyboardInterrupt()
        captured = capsys.readouterr()
        assert captured.out == "\n"
        assert captured.err == ""
