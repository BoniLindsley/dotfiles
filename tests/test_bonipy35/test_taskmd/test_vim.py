#!/usr/bin/env python3

# Standard libraries.
import json
import os
import pathlib
import shutil
import subprocess
import sys
import typing

# External dependencies.
import pytest

# Internal modules.
from bonipy35.taskmd import vim

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
_REPO_ROOT = pathlib.Path(__file__).parents[3]
_SRC_DIR = _REPO_ROOT / "src"
_SHIM_PATH = _REPO_ROOT / "vim" / "taskmd_vim.py"


def _copy_fixture(name: str, tmp_path: pathlib.Path) -> pathlib.Path:
    destination = tmp_path / name
    shutil.copy(_FIXTURES_DIR / name, destination)
    return destination


@pytest.fixture(name="runner")
def fixture_runner() -> "vim.Runner":
    """A `Runner` that always runs the *this checkout's* `bonipy35`
    package, regardless of whether it happens to be installed --
    `PYTHONPATH` is pointed straight at `src/`."""
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(_SRC_DIR) + os.pathsep + existing if existing else str(_SRC_DIR)
    )
    return vim.Runner(python=sys.executable, cwd=str(_REPO_ROOT), env=env)


# ---------------------------------------------------------------------------
# Runner: argv construction (no subprocess)
# ---------------------------------------------------------------------------


class TestRunnerArgvConstruction:
    def test_build_report_argv(self) -> None:
        runner = vim.Runner(python="python3")
        argv = runner.build_report_argv("notes.task.md", "--tag", "core")
        assert argv == [
            "python3",
            "-m",
            "bonipy35",
            "taskmd",
            "report",
            "notes.task.md",
            "--tag",
            "core",
        ]

    def test_build_clock_argv_does_not_go_through_cli_dispatch(
        self,
    ) -> None:
        # Clock commands use their direct module entry point.
        runner = vim.Runner(python="python3")
        argv = runner.build_clock_argv(
            "start", "notes.task.md", "--line", "5"
        )
        assert argv == [
            "python3",
            "-m",
            "bonipy35.taskmd.clock",
            "start",
            "notes.task.md",
            "--line",
            "5",
        ]
        assert "cli" not in argv
        assert argv[2] == "bonipy35.taskmd.clock"

    def test_defaults_use_sys_executable(self) -> None:
        runner = vim.Runner()
        assert runner.python == sys.executable

    def test_custom_modules_are_honored(self) -> None:
        runner = vim.Runner(
            app_module="myapp", clock_module="myapp.taskmd.clock"
        )
        assert runner.build_report_argv("x")[2] == "myapp"
        assert runner.build_clock_argv("x")[2] == "myapp.taskmd.clock"


class TestRunnerSubprocessPlumbing:
    def test_run_report_passes_cwd_and_env_to_subprocess(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured = {}

        def fake_run(argv, **kwargs):  # type: ignore[no-untyped-def]
            captured["argv"] = argv
            captured["kwargs"] = kwargs

            class _Completed:
                returncode = 0
                stdout = "ok\n"
                stderr = ""

            return _Completed()

        monkeypatch.setattr(subprocess, "run", fake_run)
        runner = vim.Runner(cwd="/somewhere", env={"X": "1"})
        result = runner.run_report("notes.task.md")

        assert captured["kwargs"]["cwd"] == "/somewhere"
        assert captured["kwargs"]["env"] == {"X": "1"}
        assert result.returncode == 0
        assert result.stdout == "ok\n"
        assert result.argv == captured["argv"]

    def test_run_clock_passes_cwd_and_env_to_subprocess(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured = {}

        class _Completed:
            returncode = 1
            stdout = ""
            stderr = "boom\n"

        def fake_run(argv: typing.Any, **kwargs: typing.Any) -> _Completed:
            del kwargs
            captured["argv"] = argv
            return _Completed()

        monkeypatch.setattr(subprocess, "run", fake_run)
        runner = vim.Runner()
        result = runner.run_clock("status", "notes.task.md")

        assert captured["argv"][:3] == [
            runner.python,
            "-m",
            "bonipy35.taskmd.clock",
        ]
        assert result.returncode == 1
        assert result.stderr == "boom\n"


class TestCommandResult:
    def test_repr_includes_argv_and_returncode(self) -> None:
        result = vim.CommandResult(
            argv=["a", "b"], returncode=0, stdout="", stderr=""
        )
        text = repr(result)
        assert "['a', 'b']" in text
        assert "returncode=0" in text


# ---------------------------------------------------------------------------
# Per-subcommand functions, driven against real subprocesses
# ---------------------------------------------------------------------------


class TestClockStart:
    def test_start_by_line(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        result = vim.clock_start(runner, path, line=1)
        assert result.returncode == 0
        assert "started clock" in result.stdout

    def test_start_by_task_title(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        result = vim.clock_start(
            runner, path, task_title="Add logging", note="digging in"
        )
        assert result.returncode == 0

    def test_start_already_open_is_an_error(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        result = vim.clock_start(runner, path, task_title="Write the parser")
        assert result.returncode != 0
        assert "already has an open" in result.stderr

    def test_start_lenient_flag_is_forwarded(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = tmp_path / "lower.task.md"
        path.write_text("# todo lowercase\nsome text\n")
        result = vim.clock_start(runner, path, line=1, lenient=True)
        assert result.returncode == 0


class TestClockStop:
    def test_stop_explicit_line(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        _, sessions = vim.clock_list_open(runner, path)
        assert sessions
        line = sessions[0]["line"]
        result = vim.clock_stop(runner, path, line=line, note="done")
        assert result.returncode == 0
        assert "stopped clock" in result.stdout

    def test_stop_with_explicit_time(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        vim.clock_start(runner, path, line=1)
        result = vim.clock_stop(runner, path, at="2025-07-06T18:00:00+00:00")
        assert result.returncode == 0
        assert "2025-07-06T18:00:00" in result.stdout

    def test_stop_no_open_session(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        result = vim.clock_stop(runner, path)
        assert result.returncode != 0
        assert "no open CLOCK" in result.stderr


class TestClockListOpen:
    def test_parses_json_payload(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        result, sessions = vim.clock_list_open(runner, path)
        assert result.returncode == 0
        assert sessions is not None
        assert sessions[0]["task"] == "Write the parser"
        assert "line" in sessions[0]
        assert "start" in sessions[0]

    def test_empty_when_nothing_open(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        result, sessions = vim.clock_list_open(runner, path)
        assert result.returncode == 0
        assert sessions == []

    def test_sessions_is_none_on_failure(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        missing = tmp_path / "missing.task.md"
        result, sessions = vim.clock_list_open(runner, missing)
        assert result.returncode != 0
        assert sessions is None

    def test_sessions_is_none_on_unparsable_output(self) -> None:
        class _StubRunner(vim.Runner):
            def run_clock(self, *args: str) -> vim.CommandResult:
                del args
                return vim.CommandResult(
                    argv=["stub"],
                    returncode=0,
                    stdout="not json",
                    stderr="",
                )

        result, sessions = vim.clock_list_open(
            _StubRunner(), pathlib.Path("x")
        )
        assert sessions is None
        assert result.stdout == "not json"


class TestClockStatus:
    def test_open_returns_zero(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        result = vim.clock_status(runner, path, line=1)
        assert result.returncode == 0
        assert vim.STATUS_LABELS[result.returncode] == "open"

    def test_closed_returns_one(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        result = vim.clock_status(runner, path)
        assert result.returncode == 1
        assert vim.STATUS_LABELS[result.returncode] == "closed"

    def test_not_found_returns_two(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        result = vim.clock_status(runner, path, line=9999)
        assert result.returncode == 2
        assert vim.STATUS_LABELS[result.returncode] == "task not found"


class TestReport:
    def test_report_single_file(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        result = vim.report(runner, path)
        assert result.returncode == 0
        assert "Grand total" in result.stdout

    def test_report_extra_args_forwarded(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        result = vim.report(runner, path, extra_args=["--format", "json"])
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload

    def test_report_dir(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        _copy_fixture("basic.task.md", tmp_path)
        result = vim.report_dir(runner, tmp_path)
        assert result.returncode == 0
        assert "Grand total" in result.stdout

    def test_report_dir_extra_args_forwarded(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        _copy_fixture("clocked.task.md", tmp_path)
        result = vim.report_dir(
            runner, tmp_path, extra_args=["--tag", "core"]
        )
        assert result.returncode == 0


class TestScheduleCommands:
    def test_schedule_show(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("scheduled.task.md", tmp_path)
        result = vim.schedule_show(
            runner,
            path,
            extra_args=["--from", "2025-09-01", "--to", "2025-09-20"],
        )
        assert result.returncode == 0
        assert "Focus session" in result.stdout

    def test_schedule_conflicts_none(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("scheduled.task.md", tmp_path)
        result = vim.schedule_conflicts(
            runner,
            path,
            extra_args=["--from", "2025-09-01", "--to", "2025-09-20"],
        )
        assert result.returncode == 0
        assert "no conflicts" in result.stdout

    def test_schedule_summary(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("scheduled.task.md", tmp_path)
        result = vim.schedule_summary(
            runner,
            path,
            extra_args=["--from", "2025-09-01", "--to", "2025-09-20"],
        )
        assert result.returncode == 0
        assert "Total:" in result.stdout


# ---------------------------------------------------------------------------
# resolve_and_stop: the ambiguous-session flow
# ---------------------------------------------------------------------------


class TestResolveAndStop:
    def test_no_open_sessions(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        outcome = vim.resolve_and_stop(runner, path)
        assert outcome["status"] == vim.STOP_STATUS_NONE_OPEN
        assert outcome["sessions"] == []

    def test_single_open_session_is_stopped_automatically(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        outcome = vim.resolve_and_stop(runner, path)
        assert outcome["status"] == vim.STOP_STATUS_OK
        assert "stopped clock" in outcome["result"].stdout

        # And it really is closed now.
        _, sessions = vim.clock_list_open(runner, path)
        assert sessions == []

    def test_multiple_open_sessions_are_reported_as_ambiguous(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        vim.clock_start(runner, path, task_title="Write the parser")
        vim.clock_start(runner, path, task_title="Add logging")

        outcome = vim.resolve_and_stop(runner, path)
        assert outcome["status"] == vim.STOP_STATUS_AMBIGUOUS
        assert len(outcome["sessions"]) == 2
        titles = {session["task"] for session in outcome["sessions"]}
        assert titles == {"Write the parser", "Add logging"}

    def test_explicit_line_stops_directly(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        start = vim.clock_start(runner, path, task_title="Add logging")
        assert start.returncode == 0
        _, sessions = vim.clock_list_open(runner, path)
        assert sessions
        chosen_line = sessions[0]["line"]

        outcome = vim.resolve_and_stop(runner, path, line=chosen_line)
        assert outcome["status"] == vim.STOP_STATUS_OK

    def test_explicit_line_error_is_reported(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        outcome = vim.resolve_and_stop(runner, path, line=9999)
        assert outcome["status"] == vim.STOP_STATUS_ERROR

    def test_list_open_failure_is_reported_as_error(
        self, runner: "vim.Runner", tmp_path: pathlib.Path
    ) -> None:
        missing = tmp_path / "missing.task.md"
        outcome = vim.resolve_and_stop(runner, missing)
        assert outcome["status"] == vim.STOP_STATUS_ERROR
        assert outcome["sessions"] is None

    def test_single_session_stop_failure_is_reported_as_error(self) -> None:
        # A stubbed runner: list-open reports one open session, but
        # the subsequent stop call fails anyway (e.g. a race where
        # someone else closed it in between).
        class _StubRunner(vim.Runner):
            def __init__(self) -> None:
                super().__init__()
                self.calls = []  # type: list[tuple[str, ...]]

            def run_clock(self, *args: str) -> vim.CommandResult:
                self.calls.append(args)
                if args[0] == "list-open":
                    payload = [
                        {
                            "task": "X",
                            "line": 3,
                            "start": "2025-01-01T00:00:00+00:00",
                            "description": "",
                        }
                    ]
                    return vim.CommandResult(
                        argv=["stub"],
                        returncode=0,
                        stdout=json.dumps(payload),
                        stderr="",
                    )
                return vim.CommandResult(
                    argv=["stub"], returncode=1, stdout="", stderr="race"
                )

        outcome = vim.resolve_and_stop(_StubRunner(), pathlib.Path("x"))
        assert outcome["status"] == vim.STOP_STATUS_ERROR
        assert outcome["sessions"] is not None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


class TestFormatInputlistMenu:
    def test_builds_one_line_per_session_after_the_prompt(self) -> None:
        sessions = [
            {
                "task": "Write the parser",
                "line": 5,
                "start": "2025-01-01T09:00:00+00:00",
            },
            {
                "task": "Add logging",
                "line": 10,
                "start": "2025-01-02T09:00:00+00:00",
            },
        ]
        menu = vim.format_inputlist_menu(sessions)
        assert menu[0] == "Multiple open sessions -- choose one to stop:"
        assert menu[1].startswith("1. Write the parser")
        assert menu[2].startswith("2. Add logging")

    def test_custom_prompt_is_used(self) -> None:
        menu = vim.format_inputlist_menu([], prompt="Pick one:")
        assert menu == ["Pick one:"]

    def test_missing_fields_fall_back_to_placeholder(self) -> None:
        menu = vim.format_inputlist_menu([{}])
        assert "?" in menu[1]


class TestFormatQuickfixList:
    def test_builds_one_entry_per_session(self) -> None:
        sessions = [
            {
                "task": "Write the parser",
                "line": 5,
                "start": "2025-01-01T09:00:00+00:00",
                "description": "",
            },
            {
                "task": "Add logging",
                "line": 10,
                "start": "2025-01-02T09:00:00+00:00",
                "description": "digging in",
            },
        ]
        entries = vim.format_quickfix_list("notes.task.md", sessions)
        assert entries[0]["filename"] == "notes.task.md"
        assert entries[0]["lnum"] == 5
        assert "digging in" not in entries[0]["text"]
        assert entries[1]["lnum"] == 10
        assert "digging in" in entries[1]["text"]
