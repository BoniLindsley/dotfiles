#!/usr/bin/env python3

# Standard libraries.
import collections.abc
import logging
import platform
import shlex
import subprocess
import sys
import typing

_AnyStr = typing.TypeVar("_AnyStr", bytes, str)
_FileDescriptor = None | int | typing.IO[_AnyStr]


_logger = logging.getLogger(__name__)


class Command:
    def __init__(self, *prefixes: collections.abc.Iterable[str]) -> None:
        self._arguments: list[str] = []
        """Expand underscore for autocomplete in Python shell."""
        for prefix in prefixes:
            if isinstance(prefix, str):
                prefix = shlex.split(prefix)
            self._arguments.extend(prefix)

    def __add__(self, value: collections.abc.Iterable[str]) -> "Command":
        return Command(self._arguments, value)

    def __iter__(self) -> collections.abc.Iterator[str]:
        return iter(self._arguments)


def execute(
    *args: collections.abc.Iterable[str],
    stdin: None | _FileDescriptor[str] = None,
    stdout: None | _FileDescriptor[str] = None,
) -> subprocess.Popen[str]:
    if stdin is None:
        stdin = sys.stdin
    if stdout is None:
        stdout = sys.stdout

    full_args = list(Command(*args))
    _logger.info("Executing: %s", full_args)

    with subprocess.Popen(full_args, stdin=stdin, stdout=stdout, text=True) as process:
        return process


oi = execute
"""Short-hand for `execute`. Allows autocomplete with `oi<c-i>`."""


def _pip_break_system_packages() -> list[str]:
    python_version = tuple(map(int, platform.python_version_tuple()))
    if python_version >= (3, 11, 2):
        if platform.system() == "Linux":
            os_release = platform.freedesktop_os_release()["ID"]
            if os_release == "debian":
                return ["--break-system-packages"]
    return []


class _Pip(Command):
    def __init__(self, *args: typing.Any) -> None:
        super().__init__(*args, [sys.executable, "-m", "pip"])
        self.install = self._Install(self)
        self.uninstall = self._Uninstall(self)

    class _Install(Command):
        def __init__(self, *args: typing.Any) -> None:
            super().__init__(*args, ["install", "--compile", "--upgrade"])
            self.user = self._User(self)

        class _User(Command):
            def __init__(self, *args: typing.Any) -> None:
                super().__init__(*args, ["--user"], _pip_break_system_packages())

    class _Uninstall(Command):
        def __init__(self, *args: typing.Any) -> None:
            super().__init__(*args, ["uninstall"], _pip_break_system_packages())


pip = _Pip()
