#!/usr/bin/env python3

# Standard libraries.
import inspect
import os
import pathlib

from typing import Callable, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35 import xdg
from bonipy35.xdg import (
    AppDirectories,
    config_home,
    data_home,
    ensure_directory_exists,
    home,
    state_home,
)


class TestEnsureDirectoryExists:
    def test_creates_private_ancestors(self, tmp_path: pathlib.Path) -> None:
        previous = os.umask(0o022)
        try:
            path = tmp_path / "parent" / "child"
            ensure_directory_exists(path)
        finally:
            os.umask(previous)
        assert path.is_dir()
        assert path.stat().st_mode & 0o777 == 0o700
        assert path.parent.stat().st_mode & 0o777 == 0o700

    def test_preserves_existing_directory(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = tmp_path / "existing"
        path.mkdir(mode=0o755)
        mode = path.stat().st_mode
        ensure_directory_exists(path)
        assert path.stat().st_mode == mode

    def test_rejects_existing_file(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "file"
        path.write_text("keep")
        with pytest.raises(FileExistsError):
            ensure_directory_exists(path)
        assert path.read_text() == "keep"

    def test_rejects_file_parent(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "file"
        path.write_text("keep")
        with pytest.raises(NotADirectoryError):
            ensure_directory_exists(path / "child")
        assert path.read_text() == "keep"


class TestHome:
    def test_propagates_resolution_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fail_expanduser(_path: pathlib.Path) -> pathlib.Path:
            raise RuntimeError("No home directory")

        monkeypatch.delenv("HOME", raising=False)
        monkeypatch.setattr(pathlib.Path, "expanduser", fail_expanduser)
        with pytest.raises(RuntimeError, match="No home directory"):
            inspect.unwrap(home)()

    def test_resolves_account_home(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Query the account database independently of the HOME environment.
        import pwd  # pylint: disable=import-outside-toplevel

        expected = pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir)
        monkeypatch.delenv("HOME", raising=False)
        assert inspect.unwrap(home)() == expected

    def test_uses_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", "/home/example")
        assert inspect.unwrap(home)() == pathlib.Path("/home/example")


@pytest.mark.parametrize(
    "function,variable,suffix",
    [
        (config_home, "XDG_CONFIG_HOME", ".config"),
        (data_home, "XDG_DATA_HOME", ".local/share"),
        (state_home, "XDG_STATE_HOME", ".local/state"),
    ],
)
class TestXdgHomes:
    @pytest.mark.parametrize("value", [None, "", "relative/path", "~/path"])
    def test_falls_back_for_invalid_values(
        self,
        monkeypatch: pytest.MonkeyPatch,
        function: Callable[[], pathlib.Path],
        variable: str,
        suffix: str,
        value: Union[None, str],
    ) -> None:
        monkeypatch.setattr(
            xdg, "home", lambda: pathlib.Path("/home/example")
        )
        if value is None:
            monkeypatch.delenv(variable, raising=False)
        else:
            monkeypatch.setenv(variable, value)
        assert (
            inspect.unwrap(function)()
            == pathlib.Path("/home/example") / suffix
        )

    def test_accepts_absolute_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        function: Callable[[], pathlib.Path],
        variable: str,
        suffix: str,
        tmp_path: pathlib.Path,
    ) -> None:
        path = tmp_path / suffix
        monkeypatch.setenv(variable, str(path))
        assert inspect.unwrap(function)() == path


class TestAppDirectories:
    @pytest.mark.parametrize(
        "attribute", ["config_home", "data_home", "state_home"]
    )
    def test_creates_and_caches_directory(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: pathlib.Path,
        attribute: str,
    ) -> None:
        monkeypatch.setattr(xdg, attribute, lambda: tmp_path)
        directories = AppDirectories(app_name="example")
        path = getattr(directories, attribute)
        assert path == tmp_path / "example"
        assert path.is_dir()
        assert path.stat().st_mode & 0o777 == 0o700
        assert getattr(directories, attribute) is path
