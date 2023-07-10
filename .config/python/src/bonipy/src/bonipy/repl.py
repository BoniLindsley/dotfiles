#!/usr/bin/env python3

# Standard libraries.
import builtins
import collections.abc  # pylint: disable=unused-import  # Used inside "type hints".
import datetime
import logging
import platform
import shlex
import subprocess
import sys
import typing


_logger = logging.getLogger(__name__)


class Command:
    def __init__(
        self, *nested_arguments: "collections.abc.Iterable[str] | subprocess.Popen[str]"
    ) -> None:
        """Store arguments that form a command. Lazy expansion at runtime."""
        self._nested_arguments: "list[collections.abc.Iterable[str]]" = []
        if not nested_arguments:
            try:
                nested_arguments = (builtins._,)  # type: ignore[attr-defined]
            except AttributeError:
                nested_arguments = tuple()
        for arguments in nested_arguments:
            if isinstance(arguments, str):
                self._nested_arguments.append(shlex.split(arguments))
            elif isinstance(arguments, subprocess.Popen):
                # Unsure when non-list and bytesargs may occur,
                # or how to special case it.
                arguments = arguments.args  # type: ignore[assignment]
                assert isinstance(arguments, list)
                self._nested_arguments.append(arguments)
            else:
                self._nested_arguments.append(arguments)
        self._subcommands: dict[str, "Command"] = {}

    def __add__(self, value: "collections.abc.Iterable[str]") -> "Command":
        return Command(*self._nested_arguments, value)

    def __delitem__(self, key: str) -> None:
        del self._subcommands[key]

    def __dir__(self) -> "collections.abc.Iterable[str]":
        return self._subcommands.keys()

    def __getattr__(self, key: str) -> "Command":
        return self._subcommands[key]

    def __getitem__(self, key: str) -> "Command":
        return self._subcommands[key]

    def __iter__(self) -> "collections.abc.Iterator[str]":
        for arguments in self._nested_arguments:
            yield from arguments

    def __repr__(self) -> str:
        return f"Command({list(self)})"

    def __setitem__(
        self, key: str, value: typing.Union["Command", "collections.abc.Iterable[str]"]
    ) -> None:
        self._subcommands[key] = (
            value if isinstance(value, Command) else Command(self, value)
        )


class ProcessMap:
    def __init__(self) -> None:
        self._mapping: "dict[str, subprocess.Popen[str]]" = {}

    def __delattr__(self, key: str) -> None:
        del self._mapping[key]

    def __dir__(self) -> "collections.abc.Iterable[str]":
        return self._mapping.keys()

    def __getattr__(self, key: str) -> "subprocess.Popen[str]":
        return self._mapping[key]

    def __setitem__(self, key: str, value: "subprocess.Popen[str]") -> None:
        self._mapping[key] = value

    def execute(
        self,
        *args: "collections.abc.Iterable[str]",
        stdin: "None | int | typing.IO[str]" = None,
        stdout: "None | int | typing.IO[str]" = None,
    ) -> "subprocess.Popen[str]":
        if stdin is None:
            stdin = sys.stdin
        if stdout is None:
            stdout = sys.stdout

        full_args = list(Command(*args))
        _logger.info("Executing: %s", full_args)

        with subprocess.Popen(
            full_args, stdin=stdin, stdout=stdout, universal_newlines=True
        ) as process:
            now_string = datetime.datetime.now().strftime("D%Y_%m_%d_T%H_%M_%S")
            self._mapping[f"{now_string}_P{process.pid}"] = process
            return process


oops = ProcessMap()
U = oops.execute


def _pip_break_system_packages() -> "list[str]":
    python_version = tuple(map(int, platform.python_version_tuple()))
    if python_version >= (3, 11, 2):
        if platform.system() == "Linux":
            os_release = platform.freedesktop_os_release()["ID"]
            if os_release == "debian":
                return ["--break-system-packages"]
    return []


pip = Command([sys.executable, "-m", "pip"])
pip["install"] = ["install", "--compile", "--upgrade"]
pip["install"]["user"] = ["--user", *_pip_break_system_packages()]
pip["uninstall"] = ["uninstall", *_pip_break_system_packages()]
