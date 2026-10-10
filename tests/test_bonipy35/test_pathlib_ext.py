#!/usr/bin/env python3

# Standard libraries.
import pathlib

# External dependencies.
import pytest

# Internal modules.
from bonipy35.pathlib_ext import ensure_is_dir


class TestEnsureIsDir:
    def test_creates_if_missing(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "directory"
        ensure_is_dir(path)
        assert path.is_dir()

    def test_creates_parent_if_missing(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "parent" / "child"
        ensure_is_dir(path)
        assert path.is_dir()

    def test_errors_if_file_at_parent(self, tmp_path: pathlib.Path) -> None:
        parent = tmp_path / "existing.txt"
        parent.write_text("keep this content")
        path = parent / "child"
        with pytest.raises(NotADirectoryError):
            ensure_is_dir(path)
        assert parent.read_text() == "keep this content"
        assert not path.exists()

    def test_errors_if_file_at_path(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "existing.txt"
        path.write_text("keep this content")
        with pytest.raises(FileExistsError):
            ensure_is_dir(path)
        assert path.read_text() == "keep this content"

    def test_is_idempotent(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "directory"
        ensure_is_dir(path)
        ensure_is_dir(path)
        assert path.is_dir()

    def test_noop_if_is_dir(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "directory"
        path.mkdir()
        file_path = path / "existing.txt"
        file_path.write_text("keep this content")
        ensure_is_dir(path)
        assert path.is_dir()
        assert file_path.read_text() == "keep this content"
