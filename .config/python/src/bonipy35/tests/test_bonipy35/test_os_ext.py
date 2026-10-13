#!/usr/bin/env python3

# Standard libraries.
import pathlib

# External dependencies.
import pytest

# Internal modules.
from bonipy35.os_ext import get_environ_path


class TestGetEnvironPath:
    def test_returns_none_if_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("BONIPY35_TEST_PATH", raising=False)
        assert get_environ_path("BONIPY35_TEST_PATH") is None

    @pytest.mark.parametrize(
        "value",
        ["", "relative/path", "/absolute/path", "~/path", "$HOME/path"],
    )
    def test_converts_without_expanding(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("BONIPY35_TEST_PATH", value)
        assert get_environ_path("BONIPY35_TEST_PATH") == pathlib.Path(value)
