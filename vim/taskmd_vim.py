#!/usr/bin/env python3

# Standard libraries.
import pathlib

from typing import Sequence, Union

# External dependencies.
import vim

# Internal modules.
import bonipy35.taskmd.vim

STOP_STATUS_OK = "ok"
STOP_STATUS_NONE_OPEN = "none_open"
STOP_STATUS_AMBIGUOUS = "ambiguous"
STOP_STATUS_ERROR = "error"

# Mirrors `clock.clock_status`'s exit-code convention: 0=open,
# 1=closed, 2=task not found.
STATUS_LABELS = {0: "open", 1: "closed", 2: "task not found"}

DEFAULT_APP_MODULE = "bonipy35"
DEFAULT_CLOCK_MODULE = "bonipy35.taskmd.clock"


def _echo(message: str, *, highlight: Union[None, str] = None) -> None:
    escaped = message.replace("'", "''")
    if highlight:
        vim.command("echohl {0}".format(highlight))
    vim.command("echom '{0}'".format(escaped))
    if highlight:
        vim.command("echohl None")


def _current_file() -> pathlib.Path:
    result = vim.eval("expand('%:p')")
    assert isinstance(result, str)
    return pathlib.Path(result)


def _current_line() -> int:
    result = vim.eval("line('.')")
    assert isinstance(result, str)
    return int(result)


def _open_scratch_buffer(name: str, lines: "Sequence[str]") -> None:
    vim.command("botright new")
    vim.command("setlocal buftype=nofile bufhidden=wipe noswapfile")
    vim.command("setlocal filetype=taskmd-report")
    vim.command("silent file {0}".format(name))
    vim.current.buffer[:] = list(lines) or [""]


def vim_clock_start(*, note: Union[None, str] = None) -> None:
    runner = bonipy35.taskmd.vim.Runner()
    path = _current_file()
    line = _current_line()
    result = bonipy35.taskmd.vim.clock_start(
        runner, path, line=line, note=note
    )
    if result.returncode == 0:
        _echo(result.stdout.strip())
    else:
        _echo(result.stderr.strip(), highlight="ErrorMsg")


def vim_clock_stop(
    *, chosen_line: Union[None, int] = None, note: Union[None, str] = None
) -> None:
    runner = bonipy35.taskmd.vim.Runner()
    path = _current_file()
    outcome = bonipy35.taskmd.vim.resolve_and_stop(
        runner, path, line=chosen_line, note=note
    )

    if outcome["status"] == STOP_STATUS_NONE_OPEN:
        _echo("taskmd: no open sessions in this file")
        return
    if outcome["status"] == STOP_STATUS_AMBIGUOUS:
        menu = bonipy35.taskmd.vim.format_inputlist_menu(outcome["sessions"])
        choice = int(vim.eval("inputlist({0!r})".format(menu)))
        if choice <= 0 or choice > len(outcome["sessions"]):
            _echo("taskmd: stop cancelled")
            return
        vim_clock_stop(
            chosen_line=outcome["sessions"][choice - 1]["line"], note=note
        )
        return
    if outcome["status"] == STOP_STATUS_OK:
        _echo(outcome["result"].stdout.strip())
        return
    _echo(outcome["result"].stderr.strip(), highlight="ErrorMsg")


def vim_clock_status() -> None:
    runner = bonipy35.taskmd.vim.Runner()
    path = _current_file()
    line = _current_line()
    result = bonipy35.taskmd.vim.clock_status(runner, path, line=line)
    label = STATUS_LABELS.get(result.returncode, "unknown")
    _echo("taskmd: {0}".format(label))


def vim_report() -> None:
    runner = bonipy35.taskmd.vim.Runner()
    path = _current_file()
    result = bonipy35.taskmd.vim.report(runner, path)
    if result.returncode != 0:
        _echo(result.stderr.strip(), highlight="ErrorMsg")
        return
    _open_scratch_buffer("taskmd-report", result.stdout.splitlines())


def vim_report_dir() -> None:
    runner = bonipy35.taskmd.vim.Runner()
    directory = vim.eval("expand('%:p:h')")
    result = bonipy35.taskmd.vim.report_dir(runner, directory)
    if result.returncode != 0:
        _echo(result.stderr.strip(), highlight="ErrorMsg")
        return
    _open_scratch_buffer("taskmd-report-dir", result.stdout.splitlines())


def vim_list_open() -> None:
    runner = bonipy35.taskmd.vim.Runner()
    path = _current_file()
    result, sessions = bonipy35.taskmd.vim.clock_list_open(runner, path)
    if result.returncode != 0 or sessions is None:
        _echo(result.stderr.strip(), highlight="ErrorMsg")
        return
    if not sessions:
        _echo("taskmd: no open sessions in this file")
        return
    entries = bonipy35.taskmd.vim.format_quickfix_list(path, sessions)
    vim.eval("setqflist({0!r})".format(entries))
    vim.command("copen")


def vim_schedule_show() -> None:
    runner = bonipy35.taskmd.vim.Runner()
    path = _current_file()
    result = bonipy35.taskmd.vim.schedule_show(runner, path)
    if result.returncode != 0:
        _echo(result.stderr.strip(), highlight="ErrorMsg")
        return
    _open_scratch_buffer("taskmd-schedule-show", result.stdout.splitlines())


def vim_schedule_conflicts() -> None:
    runner = bonipy35.taskmd.vim.Runner()
    path = _current_file()
    result = bonipy35.taskmd.vim.schedule_conflicts(runner, path)
    if result.returncode not in (0, 2):
        _echo(result.stderr.strip(), highlight="ErrorMsg")
        return
    lines = result.stdout.splitlines()
    entries = [
        {"filename": str(path), "lnum": 1, "text": line} for line in lines
    ]
    vim.eval("setqflist({0!r})".format(entries))
    vim.command("copen")


def vim_schedule_summary() -> None:
    runner = bonipy35.taskmd.vim.Runner()
    path = _current_file()
    result = bonipy35.taskmd.vim.schedule_summary(runner, path)
    if result.returncode != 0:
        _echo(result.stderr.strip(), highlight="ErrorMsg")
        return
    _open_scratch_buffer(
        "taskmd-schedule-summary", result.stdout.splitlines()
    )
