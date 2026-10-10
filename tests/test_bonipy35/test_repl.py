#!/usr/bin/env python3

# Standard libraries.
import builtins
import subprocess
import sys

from pathlib import Path
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.repl import Command, ProcessMap, _pip_break_system_packages, pip


class TestCommand:
    def test_composition(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(builtins, "_", raising=False)
        assert not list(Command())
        monkeypatch.setattr(builtins, "_", 'echo "two words"', raising=False)
        assert list(Command()) == ["echo", "two words"]
        command = Command("git")
        command["status"] = "status --short"
        assert list(command.status + ["--branch"]) == [
            "git",
            "status",
            "--short",
            "--branch",
        ]
        assert repr(command) == "Command(['git'])"
        assert dir(command) == ["status"]
        replacement = Command("other")
        command["other"] = replacement
        assert command["other"] is replacement
        del command["status"]
        assert not hasattr(command, "status")
        with pytest.raises(KeyError):
            _ = command["missing"]

    @pytest.mark.parametrize(
        "args", [["echo", "hello"], ("echo", "hello"), "echo hello"]
    )
    def test_process_arguments(self, args: object) -> None:
        process = Mock(spec=subprocess.Popen, args=args)
        assert list(Command(process)) == ["echo", "hello"]

    def test_bytes_process_arguments(self) -> None:
        process = Mock(spec=subprocess.Popen, args=b"echo hello")
        with pytest.raises(TypeError, match="text"):
            Command(process)

    def test_exports(self) -> None:
        namespace: dict[str, object] = {}
        # Exercise the documented wildcard import in an isolated namespace.
        # pylint: disable=exec-used
        exec("from bonipy35.repl import *", namespace)
        # pylint: enable=exec-used
        assert {name for name in namespace if name != "__builtins__"} == {
            "Command",
            "ProcessMap",
            "U",
            "oops",
            "pip",
        }
        assert list(pip.install)[:3] == [sys.executable, "-m", "pip"]
        assert list(pip.uninstall)[3] == "uninstall"


class TestProcessMap:
    def test_execute(self, tmp_path: Path) -> None:
        processes = ProcessMap()
        path = tmp_path / "output.txt"
        with path.open("w", encoding="utf-8") as output:
            process = processes.execute(
                [sys.executable, "-c", "print('hello')"],
                stdin=subprocess.DEVNULL,
                stdout=output,
            )
        assert process.returncode == 0
        assert path.read_text(encoding="utf-8") == "hello\n"
        key = dir(processes)[0]
        assert getattr(processes, key) is process
        processes["alias"] = process
        del processes.alias
        assert not hasattr(processes, "alias")
        delattr(processes, key)
        assert dir(processes) == []

    def test_default_streams(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        path = tmp_path / "streams.txt"
        with path.open("w+", encoding="utf-8") as stream:
            monkeypatch.setattr(sys, "stdin", stream)
            monkeypatch.setattr(sys, "stdout", stream)
            process = ProcessMap().execute(
                [sys.executable, "-c", "print('streams')"]
            )
        assert process.returncode == 0
        assert path.read_text(encoding="utf-8") == "streams\n"


class TestPipBreakSystemPackages:
    @pytest.mark.parametrize(
        "version,system,release,expected",
        [
            (("3", "5", "10"), "Linux", "debian", []),
            (("3", "11", "1"), "Linux", "debian", []),
            (
                ("3", "11", "2"),
                "Linux",
                "debian",
                ["--break-system-packages"],
            ),
            (("3", "13", "5"), "Windows", "debian", []),
            (("3", "13", "5"), "Linux", "ubuntu", []),
        ],
    )
    def test_platform(
        self,
        monkeypatch: pytest.MonkeyPatch,
        version: tuple[str, str, str],
        system: str,
        release: str,
        expected: list[str],
    ) -> None:
        monkeypatch.setattr("platform.python_version_tuple", lambda: version)
        monkeypatch.setattr("platform.system", lambda: system)
        monkeypatch.setattr(
            "platform.freedesktop_os_release", lambda: {"ID": release}
        )
        assert _pip_break_system_packages() == expected

    def test_unavailable_release(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "platform.python_version_tuple", lambda: ("3", "13", "5")
        )
        monkeypatch.setattr("platform.system", lambda: "Linux")
        monkeypatch.setattr(
            "platform.freedesktop_os_release", Mock(side_effect=OSError)
        )
        assert not _pip_break_system_packages()
