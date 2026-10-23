#!/usr/bin/env python3
"""Run rclone commands and report their failures."""

# Standard libraries.
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import typing

from typing import Dict, Iterable, List, Sequence, Union

Completed = typing.NamedTuple(
    "Completed", [("returncode", int), ("stdout", str), ("stderr", str)]
)


class RcloneError(Exception):
    """An rclone command could not run or exited unexpectedly."""

    def __init__(
        self,
        message: str,
        *,
        command: Sequence[str],
        returncode: Union[None, int] = None,
        stderr: str = ""
    ) -> None:
        super().__init__(message)
        self.command = list(command)
        self.returncode = returncode
        self.stderr = stderr


class Runner:
    """Run rclone with one executable and one configuration file.

    Without ``executable``, rclone is searched for on ``PATH``.
    Without ``config``, rclone uses its own default configuration.
    """

    def __init__(
        self,
        *,
        executable: Union[None, str] = None,
        config: Union[None, pathlib.Path] = None
    ) -> None:
        if executable is None:
            executable = shutil.which("rclone")
            if executable is None:
                raise RcloneError("Executable not found: rclone", command=[])
        self.executable = executable
        self.config = config

    def environment(self) -> Dict[str, str]:
        """Environment variables for an rclone process."""
        environment = dict(os.environ)
        if self.config is not None:
            environment["RCLONE_CONFIG"] = str(self.config)
        return environment

    def run(
        self,
        arguments: Sequence[str],
        *,
        stdin: str = "",
        accepted: Iterable[int] = (0,)
    ) -> Completed:
        """Run rclone, raising unless it exits with an ``accepted`` code."""
        command = [self.executable] + list(arguments)  # type: List[str]
        try:
            process = subprocess.run(
                command,
                check=False,
                env=self.environment(),
                input=stdin.encode("utf-8"),
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
        except OSError as error:
            raise RcloneError(str(error), command=command) from error
        # Rclone writes UTF-8 regardless of platform and locale.
        completed = Completed(
            returncode=process.returncode,
            stdout=process.stdout.decode("utf-8"),
            stderr=process.stderr.decode("utf-8", errors="replace"),
        )
        if completed.returncode not in accepted:
            raise RcloneError(
                "rclone exited with code {}".format(completed.returncode),
                command=command,
                returncode=completed.returncode,
                stderr=completed.stderr,
            )
        return completed

    def run_json(self, arguments: Sequence[str]) -> object:
        """Run rclone and parse its standard output as JSON."""
        completed = self.run(arguments)
        try:
            return json.loads(completed.stdout)
        except ValueError as error:
            raise RcloneError(
                "Invalid JSON from rclone: {}".format(error),
                command=[self.executable] + list(arguments),
                returncode=completed.returncode,
                stderr=completed.stderr,
            ) from error


def argument_parser(description: str) -> argparse.ArgumentParser:
    """Create a parser with options selecting rclone and its configuration."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--rclone",
        metavar="PATH",
        help="rclone executable (default: search PATH)",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        type=pathlib.Path,
        help="rclone configuration file (default: rclone's own)",
    )
    return parser


def runner_from_arguments(arguments: argparse.Namespace) -> Runner:
    """Create a runner from options added by `argument_parser`."""
    return Runner(
        executable=typing.cast(Union[None, str], arguments.rclone),
        config=typing.cast(Union[None, pathlib.Path], arguments.config),
    )


def main(argv: Union[None, List[str]] = None) -> int:
    """Run rclone with the given arguments, by default ``version``."""
    parser = argument_parser(description=typing.cast(str, main.__doc__))
    parser.add_argument(
        "rclone_arguments", nargs=argparse.REMAINDER, metavar="ARGUMENT"
    )
    arguments = parser.parse_args((sys.argv if argv is None else argv)[1:])
    try:
        completed = runner_from_arguments(arguments).run(
            arguments.rclone_arguments or ["version"], accepted=range(256)
        )
    except RcloneError as error:
        sys.stderr.write(error.stderr)
        print(error, file=sys.stderr)
        return 1
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
