#!/usr/bin/env python3

# Standard libraries.
import json
import pathlib
import subprocess
import sys
import typing

from typing import Dict, List, Sequence, Tuple, Union

STOP_STATUS_OK = "ok"
STOP_STATUS_NONE_OPEN = "none_open"
STOP_STATUS_AMBIGUOUS = "ambiguous"
STOP_STATUS_ERROR = "error"

# Mirrors `clock.clock_status`'s exit-code convention: 0=open,
# 1=closed, 2=task not found.
STATUS_LABELS = {0: "open", 1: "closed", 2: "task not found"}

DEFAULT_APP_MODULE = "bonipy35"
DEFAULT_CLOCK_MODULE = "bonipy35.taskmd.clock"


# ---------------------------------------------------------------------------
# Building and running `taskmd` CLI invocations
# ---------------------------------------------------------------------------


class CommandResult:
    """The outcome of running one `taskmd` CLI subprocess.

    `argv` is exposed (rather than hidden inside the runner) so
    tests can assert on exactly what would have been executed
    without needing a real subprocess.
    """

    def __init__(
        self,
        *,
        argv: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str
    ) -> None:
        self.argv = list(argv)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self) -> str:
        return "CommandResult(argv={0!r}, returncode={1!r})".format(
            self.argv, self.returncode
        )


class Runner:
    """Builds and executes `taskmd` CLI subprocess invocations.

    `python`, `app_module`, `clock_module`, `cwd`, and `env` are all
    overridable so tests (and unusual installs) can point this at a
    specific interpreter and checkout rather than assuming a
    `taskmd` binary is on `$PATH` -- there isn't one.
    """

    def __init__(
        self,
        *,
        app_module: Union[None, str] = None,
        clock_module: Union[None, str] = None,
        cwd: Union[None, str] = None,
        env: Union[None, Dict[str, str]] = None,
        python: Union[None, str] = None
    ) -> None:
        self.app_module = app_module or DEFAULT_APP_MODULE
        self.clock_module = clock_module or DEFAULT_CLOCK_MODULE
        self.cwd = cwd
        self.env = env
        self.python = python or sys.executable

    def build_report_argv(self, *args: str) -> List[str]:
        """Invoke report through the package dispatcher."""
        argv = [self.python, "-m", self.app_module, "taskmd"]
        argv.append("report")
        argv.extend(str(arg) for arg in args)
        return argv

    def build_clock_argv(self, *args: str) -> List[str]:
        """Invoke clock directly, without the package dispatch hops."""
        argv = [self.python, "-m", self.clock_module]
        argv.extend(str(arg) for arg in args)
        return argv

    def build_schedule_argv(self, *args: str) -> List[str]:
        """`schedule` is dispatched the same way as `report`, via
        `python3 -m bonipy35 taskmd schedule ...`."""
        argv = [self.python, "-m", self.app_module, "taskmd"]
        argv.append("schedule")
        argv.extend(str(arg) for arg in args)
        return argv

    def _run(self, argv: List[str]) -> CommandResult:
        completed = subprocess.run(  # pylint: disable=subprocess-run-check
            argv,
            cwd=self.cwd,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return CommandResult(
            argv=argv,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def run_report(self, *args: str) -> CommandResult:
        return self._run(self.build_report_argv(*args))

    def run_clock(self, *args: str) -> CommandResult:
        return self._run(self.build_clock_argv(*args))

    def run_schedule(self, *args: str) -> CommandResult:
        return self._run(self.build_schedule_argv(*args))


# ---------------------------------------------------------------------------
# One function per CLI subcommand
# ---------------------------------------------------------------------------


def _mode_flag(lenient: bool) -> "List[str]":
    return ["--lenient"] if lenient else []


def clock_start(  # pylint: disable=too-many-arguments
    runner: Runner,
    path: pathlib.Path,
    *,
    lenient: bool = False,
    line: Union[None, int] = None,
    note: Union[None, str] = None,
    task_title: Union[None, str] = None
) -> CommandResult:
    """Run `taskmd clock start`. Exactly one of `line` /
    `task_title` should be given (the CLI enforces this itself)."""
    args = ["start", str(path)]
    if line is not None:
        args += ["--line", str(line)]
    if task_title is not None:
        args += ["--task-title", task_title]
    if note is not None:
        args += ["--note", note]
    args += _mode_flag(lenient)
    return runner.run_clock(*args)


def clock_stop(  # pylint: disable=too-many-arguments
    runner: Runner,
    path: pathlib.Path,
    *,
    at: Union[None, str] = None,
    lenient: bool = False,
    line: Union[None, int] = None,
    note: Union[None, str] = None
) -> CommandResult:
    """Run `taskmd clock stop` directly for a known `line` (or the
    file's single open session, if `line` is omitted). For the
    "ambiguous session" flow used by `:TaskmdClockStop`, use
    `resolve_and_stop` instead."""
    args = ["stop", str(path)]
    if line is not None:
        args += ["--line", str(line)]
    if note is not None:
        args += ["--note", note]
    if at is not None:
        args += ["--time", at]
    args += _mode_flag(lenient)
    return runner.run_clock(*args)


def clock_list_open(
    runner: Runner, path: pathlib.Path, *, lenient: bool = False
) -> Tuple[CommandResult, Union[None, List[Dict[str, typing.Any]]]]:
    """Run `taskmd clock list-open`. Returns `(result, sessions)`
    where `sessions` is the parsed JSON list on success, or `None`
    if the command failed or its output wasn't valid JSON."""
    args = ["list-open", str(path)] + _mode_flag(lenient)
    result = runner.run_clock(*args)
    sessions = None
    if result.returncode == 0:
        try:
            sessions = json.loads(result.stdout)
        except ValueError:
            sessions = None
    return result, sessions


def clock_status(
    runner: Runner,
    path: pathlib.Path,
    *,
    lenient: bool = False,
    line: Union[None, int] = None
) -> CommandResult:
    """Run `taskmd clock status`. `result.returncode` is the
    0=open/1=closed/2=not-found status; look it up in
    `STATUS_LABELS` for the human-readable form."""
    args = ["status", str(path)]
    if line is not None:
        args += ["--line", str(line)]
    args += _mode_flag(lenient)
    return runner.run_clock(*args)


def report(
    runner: Runner,
    path: pathlib.Path,
    *,
    extra_args: Union[None, Sequence[str]] = None,
    lenient: bool = False
) -> CommandResult:
    """Run `taskmd report` against a single file."""
    args = [str(path)] + _mode_flag(lenient)
    if extra_args:
        args += list(extra_args)
    return runner.run_report(*args)


def report_dir(
    runner: Runner,
    directory: pathlib.Path,
    *,
    extra_args: Union[None, Sequence[str]] = None,
    lenient: bool = False
) -> CommandResult:
    """Run `taskmd report --dir` against a directory."""
    args = ["--dir", str(directory)] + _mode_flag(lenient)
    if extra_args:
        args += list(extra_args)
    return runner.run_report(*args)


def schedule_show(
    runner: Runner,
    path: pathlib.Path,
    *,
    extra_args: Union[None, Sequence[str]] = None,
    lenient: bool = False
) -> CommandResult:
    """Run `taskmd schedule show` against a single file."""
    args = ["show", str(path)] + _mode_flag(lenient)
    if extra_args:
        args += list(extra_args)
    return runner.run_schedule(*args)


def schedule_conflicts(
    runner: Runner,
    path: pathlib.Path,
    *,
    extra_args: Union[None, Sequence[str]] = None,
    lenient: bool = False
) -> CommandResult:
    """Run `taskmd schedule conflicts` against a single file."""
    args = ["conflicts", str(path)] + _mode_flag(lenient)
    if extra_args:
        args += list(extra_args)
    return runner.run_schedule(*args)


def schedule_summary(
    runner: Runner,
    path: pathlib.Path,
    *,
    extra_args: Union[None, Sequence[str]] = None,
    lenient: bool = False
) -> CommandResult:
    """Run `taskmd schedule summary` against a single file."""
    args = ["summary", str(path)] + _mode_flag(lenient)
    if extra_args:
        args += list(extra_args)
    return runner.run_schedule(*args)


# ---------------------------------------------------------------------------
# Ambiguous-stop flow: list-open, then stop
# ---------------------------------------------------------------------------


def resolve_and_stop(  # pylint: disable=too-many-arguments
    runner: Runner,
    path: pathlib.Path,
    *,
    at: Union[None, str] = None,
    lenient: bool = False,
    line: Union[None, int] = None,
    note: Union[None, str] = None
) -> Dict[str, typing.Any]:
    """High-level flow behind `:TaskmdClockStop`.

    If `line` is given (the caller already knows which session to
    close -- e.g. re-invoking after an `inputlist()` choice), stop
    it directly. Otherwise, run `clock list-open` first: zero open
    sessions -> nothing to do; exactly one -> stop it directly; more
    than one -> return the candidate list as data (`status`
    `"ambiguous"`, `"sessions"` populated) so the caller can build an
    `inputlist()` menu and call this again with the chosen `line`.

    Returns a dict with keys `status` (one of `STOP_STATUS_OK`,
    `STOP_STATUS_NONE_OPEN`, `STOP_STATUS_AMBIGUOUS`,
    `STOP_STATUS_ERROR`), `result` (the relevant `CommandResult`),
    and `sessions` (the parsed `list-open` payload, or `None`).
    """
    if line is not None:
        result = clock_stop(
            runner, path, line=line, note=note, at=at, lenient=lenient
        )
        status = (
            STOP_STATUS_OK if result.returncode == 0 else (STOP_STATUS_ERROR)
        )
        return {"result": result, "sessions": None, "status": status}

    list_result, sessions = clock_list_open(runner, path, lenient=lenient)
    if list_result.returncode != 0 or sessions is None:
        return {
            "result": list_result,
            "sessions": None,
            "status": STOP_STATUS_ERROR,
        }
    if not sessions:
        return {
            "result": list_result,
            "sessions": [],
            "status": STOP_STATUS_NONE_OPEN,
        }
    if len(sessions) == 1:
        chosen_line = sessions[0]["line"]
        result = clock_stop(
            runner,
            path,
            line=chosen_line,
            note=note,
            at=at,
            lenient=lenient,
        )
        status = (
            STOP_STATUS_OK if result.returncode == 0 else (STOP_STATUS_ERROR)
        )
        return {"result": result, "sessions": sessions, "status": status}
    return {
        "result": list_result,
        "sessions": sessions,
        "status": STOP_STATUS_AMBIGUOUS,
    }


def format_inputlist_menu(
    sessions: Sequence[Dict[str, typing.Any]],
    *,
    prompt: str = "Multiple open sessions -- choose one to stop:"
) -> "List[str]":
    """Build the list of strings `inputlist()` expects: a leading
    prompt line, then one 1-indexed line per session. The index the
    user picks (`inputlist()`'s return value) maps directly to
    `sessions[index - 1]`; `0` means the user cancelled."""
    lines = [prompt]
    for index, session in enumerate(sessions, start=1):
        lines.append(
            "{0}. {1} (line {2}, started {3})".format(
                index,
                session.get("task", "?"),
                session.get("line", "?"),
                session.get("start", "?"),
            )
        )
    return lines


if typing.TYPE_CHECKING:
    QuicklistRow = typing.TypedDict(
        "QuicklistRow", {"filename": str, "lnum": int, "text": str}
    )
else:
    # TypedDict is only needed by development tools, not Python 3.5.
    QuicklistRow = dict


def format_quickfix_list(
    path: str, sessions: Sequence[Dict[str, typing.Any]]
) -> List[QuicklistRow]:
    """Build entries suitable for Vim's `setqflist()`, one per open
    session in `sessions` (as returned by `clock_list_open`)."""
    return [
        {
            "filename": str(path),
            "lnum": session.get("line", 1),
            "text": "{0} -- started {1}{2}".format(
                session.get("task", "?"),
                session.get("start", "?"),
                (
                    " ({0})".format(session["description"])
                    if session.get("description")
                    else ""
                ),
            ),
        }
        for session in sessions
    ]
