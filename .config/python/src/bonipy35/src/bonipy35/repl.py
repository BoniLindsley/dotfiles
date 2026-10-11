#!/usr/bin/env python3

"""Command helpers for ``from bonipy35.repl import *`` in a Python REPL.

``Command("git")["status"]`` builds reusable commands; ``U(command)`` runs
one synchronously and returns its completed Popen object. ``Command()`` uses
Python's last displayed result (``builtins._``), when available. ``oops`` keeps
processes accessible by name for inspection, and ``pip.install.user`` builds
a pip command for the current interpreter. Strings use shell-style quoting,
but execution never invokes a shell.
"""

# Standard libraries.
import builtins
import datetime
import logging
import platform
import shlex
import subprocess
import sys
import typing

from typing import List, Union

__all__ = ["Command", "ProcessMap", "U", "oops", "pip"]

_logger = logging.getLogger(__name__)


class Command:
    def __init__(
        self,
        *nested_arguments: Union[
            str, typing.Iterable[str], "subprocess.Popen[str]"
        ]
    ) -> None:
        """Store arguments that form a command. Lazy expansion at runtime."""
        self._nested_arguments = []  # type: list[typing.Iterable[str]]
        if not nested_arguments:
            try:
                nested_arguments = (builtins._,)  # type: ignore[attr-defined]
            except AttributeError:
                nested_arguments = tuple()
        for arguments in nested_arguments:
            if isinstance(arguments, str):
                self._nested_arguments.append(shlex.split(arguments))
            elif isinstance(arguments, subprocess.Popen):
                process_args = arguments.args
                if isinstance(process_args, str):
                    self._nested_arguments.append(shlex.split(process_args))
                else:
                    if not isinstance(process_args, (list, tuple)):
                        raise TypeError("Command arguments must be text")
                    self._nested_arguments.append(
                        [str(argument) for argument in process_args]
                    )
            else:
                self._nested_arguments.append(arguments)
        self._subcommands = {}  # type: dict[str, "Command"]

    def __add__(self, value: typing.Iterable[str]) -> "typing.Self":
        return type(self)(*self._nested_arguments, value)

    def __delitem__(self, key: str) -> None:
        del self._subcommands[key]

    def __dir__(self) -> typing.Iterable[str]:
        return self._subcommands.keys()

    def __getattr__(self, key: str) -> "Command":
        try:
            return self._subcommands[key]
        except KeyError:
            raise AttributeError(key) from None

    def __getitem__(self, key: str) -> "Command":
        return self._subcommands[key]

    def __iter__(self) -> typing.Iterator[str]:
        for arguments in self._nested_arguments:
            yield from arguments

    def __repr__(self) -> str:
        return "Command(" + repr(list(self)) + ")"

    def __setitem__(
        self, key: str, value: Union["Command", typing.Iterable[str]]
    ) -> None:
        self._subcommands[key] = (
            value if isinstance(value, Command) else Command(self, value)
        )


class ProcessMap:
    def __init__(self) -> None:
        self._mapping = {}  # type: "dict[str, subprocess.Popen[str]]"

    def __delattr__(self, key: str) -> None:
        del self._mapping[key]

    def __dir__(self) -> typing.Iterable[str]:
        return self._mapping.keys()

    def __getattr__(self, key: str) -> "subprocess.Popen[str]":
        try:
            return self._mapping[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setitem__(self, key: str, value: "subprocess.Popen[str]") -> None:
        self._mapping[key] = value

    def execute(
        self,
        *args: Union[str, typing.Iterable[str], "subprocess.Popen[str]"],
        stdin: Union[None, int, typing.IO[str]] = None,
        stdout: Union[None, int, typing.IO[str]] = None
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
            now_string = datetime.datetime.now().strftime(
                "D%Y_%m_%d_T%H_%M_%S"
            )
            self._mapping[str(now_string) + "_P" + str(process.pid)] = process
            return process


oops = ProcessMap()
U = oops.execute


def _pip_break_system_packages() -> List[str]:
    python_version = tuple(map(int, platform.python_version_tuple()))
    if python_version >= (3, 11, 2):
        if platform.system() == "Linux":
            try:
                freedesktop_os_release = platform.freedesktop_os_release()
            except OSError:
                # Raises when trying to access /etc nor /usr/lib on Termux.
                freedesktop_os_release = {}
            os_release = freedesktop_os_release.get("ID")
            if os_release == "debian":
                return ["--break-system-packages"]
    return []


pip = Command([sys.executable, "-m", "pip"])
pip["install"] = ["install", "--compile", "--upgrade"]
pip["install"]["user"] = ["--user", *_pip_break_system_packages()]
pip["uninstall"] = ["uninstall", *_pip_break_system_packages()]
