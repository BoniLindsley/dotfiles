#!/usr/bin/env python3

"""Regression coverage for `vim/taskmd_vim.py`.

`vim/taskmd_vim.py` requires `import vim`, which only exists inside a
running Vim/Neovim process with `+python3`, so it is not (and cannot
easily be) covered by the normal `pytest` / `mypy` / `pylint` /
`black --check` gates (all scoped to `src`/`bonipy35`; see
`README.md`'s "Status" section). That is how three real bugs (two
stray `vim = vim` lines causing `UnboundLocalError`, one unqualified
`resolve_and_stop` causing `NameError`) went unnoticed for a while.

This test installs a minimal functional fake into
`sys.modules["vim"]` before importing the shim -- the same trick
Vim's embedded Python host uses to pre-populate `sys.modules` -- so
the module can be imported and its functions exercised outside Vim.
`bonipy35.taskmd.vim` (the real, fully-tested logic layer) is
monkeypatched at the function level so no subprocess is spawned.
"""

# Standard libraries.
import importlib.util
import pathlib
import sys
import types
import typing

from typing import Any, Dict, List

# External dependencies.
import pytest

# Internal modules.
import bonipy35.taskmd.vim as real_vim

_REPO_ROOT = pathlib.Path(__file__).parents[3]
_SHIM_PATH = _REPO_ROOT / "vim" / "taskmd_vim.py"


class TestVimOpen:
    def test_opens_default_document(
        self,
        shim: "types.ModuleType",
        fake_vim: "FakeVim",
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        directory = tmp_path / "tasks with 'quotes'"
        monkeypatch.setenv("TASKMD_DIR", str(directory))
        shim.vim_open()
        assert directory.is_dir()
        assert not (directory / "main.task.md").exists()
        quoted = str(directory / "main.task.md").replace("'", "''")
        assert fake_vim.commands == [
            "execute 'edit ' . fnameescape('{0}')".format(quoted)
        ]


class _FakeBuffer:
    def __init__(self) -> None:
        self.lines = []  # type: List[str]

    def __setitem__(self, _key: object, value: List[str]) -> None:
        self.lines = list(value)


class FakeVim:
    """Just enough of the `vim` module's surface for `taskmd_vim.py`
    to run against outside a real Vim process."""

    def __init__(
        self, *, current_file: str = "/tmp/x.task.md", current_line: str = "3"
    ) -> None:
        self.commands = []  # type: List[str]
        self.current_file = current_file
        self.current_line = current_line
        self.current = types.SimpleNamespace(buffer=_FakeBuffer())
        self.inputlist_choice = 1
        self.qflist = None  # type: typing.Optional[str]

    def command(self, text: str) -> None:
        self.commands.append(text)

    def eval(self, expression: str) -> str:
        if expression == "expand('%:p')":
            return self.current_file
        if expression == "expand('%:p:h')":
            return str(pathlib.Path(self.current_file).parent)
        if expression == "line('.')":
            return self.current_line
        if expression.startswith("inputlist("):
            return str(self.inputlist_choice)
        if expression.startswith("setqflist("):
            self.qflist = expression
            return "0"
        raise AssertionError(
            "unexpected vim.eval call: {0!r}".format(expression)
        )


@pytest.fixture(name="fake_vim")
def fixture_fake_vim() -> FakeVim:
    return FakeVim()


@pytest.fixture(name="shim")
def fixture_shim(fake_vim: FakeVim) -> "types.ModuleType":
    """Import a fresh copy of `vim/taskmd_vim.py` with `fake_vim`
    installed as `sys.modules["vim"]`. A fresh module object is used
    every time (rather than relying on the normal import cache)
    because the module does `import vim` at module scope: once
    bound, that name would keep pointing at whichever fake was
    installed at import time."""
    previous = sys.modules.get("vim")
    sys.modules["vim"] = typing.cast(types.ModuleType, fake_vim)
    try:
        spec = importlib.util.spec_from_file_location(
            "taskmd_vim_under_test", _SHIM_PATH
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            del sys.modules["vim"]
        else:
            sys.modules["vim"] = previous
    return module


def _stub_result(
    *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> real_vim.CommandResult:
    return real_vim.CommandResult(
        argv=["stub"], returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestVimClockStart:
    def test_success_echoes_stdout(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "clock_start",
            lambda *a, **k: _stub_result(stdout="started clock"),
        )
        shim.vim_clock_start()
        assert any("started clock" in cmd for cmd in fake_vim.commands)


class TestVimClockStatus:
    def test_echoes_label(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim, "clock_status", lambda *a, **k: _stub_result()
        )
        shim.vim_clock_status()
        assert any("open" in cmd for cmd in fake_vim.commands)


class TestVimClockStop:
    """Regression guard for the documented `resolve_and_stop`
    `NameError`: this only passes if `vim_clock_stop` calls the
    fully-qualified `bonipy35.taskmd.vim.resolve_and_stop`."""

    def test_ok_status_echoes_result(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "resolve_and_stop",
            lambda *a, **k: {
                "status": real_vim.STOP_STATUS_OK,
                "result": _stub_result(stdout="stopped clock"),
                "sessions": None,
            },
        )
        shim.vim_clock_stop()
        assert any("stopped clock" in cmd for cmd in fake_vim.commands)

    def test_none_open(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "resolve_and_stop",
            lambda *a, **k: {
                "status": real_vim.STOP_STATUS_NONE_OPEN,
                "result": _stub_result(),
                "sessions": [],
            },
        )
        shim.vim_clock_stop()
        assert any("no open sessions" in cmd for cmd in fake_vim.commands)

    def test_ambiguous_prompts_and_recurses(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sessions = [
            {
                "task": "A",
                "line": 3,
                "start": "2025-01-01T00:00:00+00:00",
                "description": "",
            },
            {
                "task": "B",
                "line": 8,
                "start": "2025-01-02T00:00:00+00:00",
                "description": "",
            },
        ]
        calls = []  # type: List[typing.Optional[int]]

        def _fake_resolve(
            *_args: object,
            line: typing.Optional[int] = None,
            **_kwargs: object
        ) -> Dict[str, Any]:
            calls.append(line)
            if line is None:
                return {
                    "status": real_vim.STOP_STATUS_AMBIGUOUS,
                    "result": _stub_result(),
                    "sessions": sessions,
                }
            return {
                "status": real_vim.STOP_STATUS_OK,
                "result": _stub_result(stdout="stopped clock"),
                "sessions": sessions,
            }

        monkeypatch.setattr(real_vim, "resolve_and_stop", _fake_resolve)
        fake_vim.inputlist_choice = 2
        shim.vim_clock_stop()
        assert calls == [None, 8]
        assert any("stopped clock" in cmd for cmd in fake_vim.commands)

    def test_ambiguous_cancelled(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "resolve_and_stop",
            lambda *a, **k: {
                "status": real_vim.STOP_STATUS_AMBIGUOUS,
                "result": _stub_result(),
                "sessions": [
                    {
                        "task": "A",
                        "line": 3,
                        "start": "x",
                        "description": "",
                    }
                ],
            },
        )
        fake_vim.inputlist_choice = 0
        shim.vim_clock_stop()
        assert any("cancelled" in cmd for cmd in fake_vim.commands)

    def test_error_status_echoes_stderr(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "resolve_and_stop",
            lambda *a, **k: {
                "status": real_vim.STOP_STATUS_ERROR,
                "result": _stub_result(stderr="boom"),
                "sessions": None,
            },
        )
        shim.vim_clock_stop()
        assert any("boom" in cmd for cmd in fake_vim.commands)


class TestVimReportAndReportDir:
    """Regression guard for the documented `_open_scratch_buffer`
    `UnboundLocalError` (the stray `vim = vim` line): these only pass
    if the helper runs to completion."""

    def test_report_opens_scratch_buffer(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "report",
            lambda *a, **k: _stub_result(stdout="line1\nline2"),
        )
        shim.vim_report()
        assert fake_vim.current.buffer.lines == ["line1", "line2"]
        assert any("botright new" in cmd for cmd in fake_vim.commands)

    def test_report_error_echoes_stderr(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "report",
            lambda *a, **k: _stub_result(returncode=1, stderr="bad"),
        )
        shim.vim_report()
        assert any("bad" in cmd for cmd in fake_vim.commands)

    def test_report_dir_opens_scratch_buffer(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "report_dir",
            lambda *a, **k: _stub_result(stdout="line1"),
        )
        shim.vim_report_dir()
        assert fake_vim.current.buffer.lines == ["line1"]


class TestVimListOpen:
    """Regression guard for the documented `vim_list_open`
    `UnboundLocalError` (the second stray `vim = vim` line)."""

    def test_populates_quickfix_list(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sessions = [
            {
                "task": "A",
                "line": 3,
                "start": "2025-01-01T00:00:00+00:00",
                "description": "",
            }
        ]
        monkeypatch.setattr(
            real_vim,
            "clock_list_open",
            lambda *a, **k: (_stub_result(), sessions),
        )
        shim.vim_list_open()
        assert fake_vim.qflist is not None
        assert any("copen" in cmd for cmd in fake_vim.commands)

    def test_no_open_sessions(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim, "clock_list_open", lambda *a, **k: (_stub_result(), [])
        )
        shim.vim_list_open()
        assert any("no open sessions" in cmd for cmd in fake_vim.commands)

    def test_error_echoes_stderr(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "clock_list_open",
            lambda *a, **k: (
                _stub_result(returncode=1, stderr="broken"),
                None,
            ),
        )
        shim.vim_list_open()
        assert any("broken" in cmd for cmd in fake_vim.commands)


class TestVimSchedule:
    def test_schedule_show_opens_scratch_buffer(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "schedule_show",
            lambda *a, **k: _stub_result(stdout="Mon 2025-09-01"),
        )
        shim.vim_schedule_show()
        assert fake_vim.current.buffer.lines == ["Mon 2025-09-01"]

    def test_schedule_conflicts_populates_quickfix(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "schedule_conflicts",
            lambda *a, **k: _stub_result(
                returncode=2, stdout="A overlaps B by 30m"
            ),
        )
        shim.vim_schedule_conflicts()
        assert fake_vim.qflist is not None
        assert any("copen" in cmd for cmd in fake_vim.commands)

    def test_schedule_summary_opens_scratch_buffer(
        self,
        shim: "types.ModuleType",
        fake_vim: FakeVim,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            real_vim,
            "schedule_summary",
            lambda *a, **k: _stub_result(stdout="Total: 1 events"),
        )
        shim.vim_schedule_summary()
        assert fake_vim.current.buffer.lines == ["Total: 1 events"]
