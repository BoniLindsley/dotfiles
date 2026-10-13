#!/usr/bin/env python3

# Standard libraries.
import pathlib

from typing import Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35 import xdg
from bonipy35.taskmd.paths import default_directory, default_document
from bonipy35.taskmd.report import discover_paths


class TestDefaultDirectory:
    @pytest.mark.parametrize("value", [None, ""])
    def test_xdg_fallback(
        self,
        value: Union[None, str],
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("TASKMD_DIR", raising=False)
        if value is not None:
            monkeypatch.setenv("TASKMD_DIR", value)
        monkeypatch.setattr(xdg, "data_home", lambda: tmp_path)
        assert default_directory() == tmp_path / "bonipy35" / "taskmd"
        assert not default_directory().exists()

    def test_environment_override(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TASKMD_DIR", str(tmp_path))
        task = tmp_path / "main.task.md"
        task.write_text("# TODO A task\n")
        assert default_directory() == tmp_path
        assert discover_paths() == [task]
        assert discover_paths(files=["explicit.task.md"]) == [
            pathlib.Path("explicit.task.md")
        ]

    def test_expand_home(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("TASKMD_DIR", "~/tasks")
        assert default_directory() == tmp_path / "tasks"


class TestDefaultDocument:
    def test_main_document(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TASKMD_DIR", str(tmp_path / "tasks"))
        assert default_document() == tmp_path / "tasks" / "main.task.md"
        assert not default_document().parent.exists()
