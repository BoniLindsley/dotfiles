#!/usr/bin/env python3

"""Real headless-`nvim` integration coverage for the `taskmd` Vim plugin.

Everything else exercising the Vim integration stops short of Vim
itself:

- `test_vim.py` unit-tests `bonipy35.taskmd.vim.Runner` and friends
  with real `subprocess` calls to the real CLI, but no `vim`/`nvim`
  process is ever started.
- `test_vim_shim.py` unit-tests `vim/taskmd_vim.py` against a fake
  `sys.modules["vim"]`, so it never touches real Vimscript either.

Neither would catch a bug in `vim/autoload/taskmd.vim` itself, or in
`vim/ftdetect/taskmd.vim`'s filetype-matching patterns. This module
closes that gap by driving the actual plugin -- Vimscript included --
through a real `nvim --headless` subprocess, using the same
`vim/`-directory-on-the-runtimepath setup a plugin manager would use
for a real install (see `utils/vimrc`/`utils/tinker.sh` for the
interactive equivalent of this).

Requires `nvim` (with `+python3`, i.e. `python3-pynvim`) on `$PATH`;
every test here is skipped, not failed, if it's absent -- see
`README.md`'s "Status" section for how to install it and confirm it's
working. Also requires `bonipy35` to be importable by whichever
Python `nvim`'s embedded `python3` host resolves to. Rather than
assume that's already been arranged (as `utils/tinker.sh` does, by
checking and `pip install -e`-ing into the system interpreter), every
`nvim` subprocess launched here gets `PYTHONPATH` pointed straight at
this checkout's `src/`, the same trick `test_vim.py`'s `runner`
fixture uses for the plain-subprocess `Runner` tests -- so these
tests are self-sufficient regardless of whatever else happens to be
installed system-wide.

Out of scope for `pyproject.toml`'s `fail_under = 100` coverage gate:
`coverage.py`'s in-process tracing can't see across a `subprocess.run`
boundary (there's no `COVERAGE_PROCESS_START` set up here), so nothing
in this file ever registers against `--cov=src` regardless of whether
it runs -- no extra marker bookkeeping needed to keep it out of that
gate. A `pytest.mark.integration` marker is still applied, for anyone
who wants to explicitly include or exclude this slower, `nvim`-
dependent tier (e.g. `pytest -m "not integration"` /
`pytest -m integration`). The marker is registered in `pyproject.toml`.
"""

# Standard libraries.
import datetime
import os
import pathlib
import shutil
import subprocess
import time

from typing import Dict, List, Optional, Sequence

# External dependencies.
import pytest

_REPO_ROOT = pathlib.Path(__file__).parents[3]
_VIM_DIR = _REPO_ROOT / "vim"
_SRC_DIR = _REPO_ROOT / "src"
_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"

NVIM = shutil.which("nvim")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        NVIM is None,
        reason=(
            "nvim not installed -- see README.md's 'Status' section "
            "for `apt-get install -y --fix-missing neovim` and how to "
            "confirm +python3 support"
        ),
    ),
]


@pytest.fixture(name="nvim_path", scope="session")
def fixture_nvim_path() -> pathlib.Path:
    nvim_path = NVIM
    if nvim_path is None:
        pytest.skip("Executable not available: nvim")
    return pathlib.Path(nvim_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _nvim_env() -> Dict[str, str]:
    """`nvim`'s embedded python3 host needs `import bonipy35...` to
    work. Point `PYTHONPATH` at this checkout's `src/` directly
    rather than assuming the package is already installed somewhere
    the system python3 can see it (mirrors `test_vim.py`'s `runner`
    fixture)."""
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(_SRC_DIR) + os.pathsep + existing if existing else str(_SRC_DIR)
    )
    return env


def _copy_fixture(name: str, tmp_path: pathlib.Path) -> pathlib.Path:
    destination = tmp_path / name
    shutil.copy(_FIXTURES_DIR / name, destination)
    return destination


def _write_task_file(
    tmp_path: pathlib.Path, name: str, content: str
) -> pathlib.Path:
    destination = tmp_path / name
    destination.write_text(content)
    return destination


def _run_nvim_batch(
    nvim_path: pathlib.Path,
    target: pathlib.Path,
    commands: Sequence[str],
    *,
    cursor_line: Optional[int] = None,
    timeout: float = 10,
) -> "subprocess.CompletedProcess[str]":
    """Run a one-shot headless `nvim`: load the plugin, `edit` a
    file, optionally move the cursor, run `commands` in order, then
    quit. Used for every command except the ambiguous-stop flow,
    which needs a long-lived server (see `_run_ambiguous_stop`)."""
    argv = [
        str(nvim_path),
        "--headless",
        "-Nu",
        "NONE",
        "-c",
        "set rtp+={0}".format(_VIM_DIR),
        "-c",
        "filetype plugin on",
        "-c",
        "edit {0}".format(target),
    ]
    if cursor_line is not None:
        argv += ["-c", "call cursor({0},1)".format(cursor_line)]
    for command in commands:
        argv += ["-c", command]
    argv += ["-c", "qa!"]
    return subprocess.run(
        argv,
        check=True,
        capture_output=True,
        timeout=timeout,
        env=_nvim_env(),
        universal_newlines=True,
    )


def _run_and_dump_buffer(
    nvim_path: pathlib.Path,
    target: pathlib.Path,
    command: str,
    tmp_path: pathlib.Path,
    *,
    cursor_line: Optional[int] = None,
) -> List[str]:
    """Run `command` (expected to open a scratch buffer, e.g.
    `:TaskmdReport`), dump the resulting current buffer to a file
    from within Vimscript, and return its lines."""
    out_path = tmp_path / "buffer_dump.txt"
    _run_nvim_batch(
        nvim_path,
        target,
        [
            command,
            "call writefile(getline(1, '$'), '{0}')".format(out_path),
        ],
        cursor_line=cursor_line,
    )
    return out_path.read_text().splitlines()


def _run_and_dump_quickfix(
    nvim_path: pathlib.Path,
    target: pathlib.Path,
    command: str,
    tmp_path: pathlib.Path,
    *,
    cursor_line: Optional[int] = None,
) -> List[str]:
    """Run `command` (expected to populate the quickfix list, e.g.
    `:TaskmdListOpen`), dump the `text` field of every quickfix entry
    to a file, and return the lines."""
    out_path = tmp_path / "quickfix_dump.txt"
    _run_nvim_batch(
        nvim_path,
        target,
        [
            command,
            "call writefile(map(getqflist(), {{_, v -> v.text}}), "
            "'{0}')".format(out_path),
        ],
        cursor_line=cursor_line,
    )
    return out_path.read_text().splitlines()


def _run_and_capture_echo(
    nvim_path: pathlib.Path,
    target: pathlib.Path,
    command: str,
    tmp_path: pathlib.Path,
    *,
    cursor_line: Optional[int] = None,
) -> str:
    """Run `command` (expected to `:echom` its result, e.g.
    `:TaskmdClockStatus`), capturing the echo area via `:redir`."""
    out_path = tmp_path / "echo_dump.txt"
    _run_nvim_batch(
        nvim_path,
        target,
        [
            "redir! > {0}".format(out_path),
            command,
            "redir END",
        ],
        cursor_line=cursor_line,
    )
    return out_path.read_text()


def _wait_for_socket(sock: pathlib.Path, timeout: float = 10) -> None:
    deadline = time.time() + timeout
    while not sock.exists():
        if time.time() > deadline:
            raise TimeoutError(
                "nvim --listen socket never appeared: {0}".format(sock)
            )
        time.sleep(0.05)


def _remote_send(
    nvim_path: pathlib.Path,
    sock: pathlib.Path,
    keys: str,
    timeout: float = 10,
) -> None:
    subprocess.run(
        [str(nvim_path), "--server", str(sock), "--remote-send", keys],
        check=True,
        capture_output=True,
        timeout=timeout,
        env=_nvim_env(),
        universal_newlines=True,
    )


def _run_ambiguous_stop(
    nvim_path: pathlib.Path,
    target: pathlib.Path,
    tmp_path: pathlib.Path,
    *,
    choice: int,
) -> None:
    """Drive `:TaskmdClockStop` through its ambiguous-session path.

    `inputlist()` genuinely blocks Neovim's main loop waiting for
    keyboard/RPC input -- there is no hook in `taskmd_vim.py` to stub
    it out, and it can't be answered from the same batch of `-c`
    flags used for every other command here (those are all queued up
    and run to completion, in order, before Neovim ever processes
    further input -- `-c "let g:x = 1"` after a command that's
    blocked in `inputlist()` never gets a chance to run).

    Instead this starts a long-lived headless server
    (`--listen <socket>`) and acts as its own remote client: one
    `nvim --server <socket> --remote-send` call injects the keys that
    invoke `:TaskmdClockStop` (which is queued as real terminal
    input, not evaluated synchronously, so this returns immediately
    without waiting for the command to finish), a second, later call
    injects the numeric answer (plus Enter) that resolves the still-
    open `inputlist()` prompt. This mirrors exactly what a human
    typing at the keyboard would send, just replayed by another
    process -- it isn't a simulation of `inputlist()`, it's the real
    thing, answered non-interactively. Confirmed to work by hand
    before being encoded here (see the session notes this test module
    was built from).
    """
    sock = tmp_path / "nvim.sock"
    proc = subprocess.Popen(  # pylint: disable=consider-using-with
        [
            str(nvim_path),
            "--headless",
            "-Nu",
            "NONE",
            "--listen",
            str(sock),
            "-c",
            "set rtp+={0}".format(_VIM_DIR),
            "-c",
            "filetype plugin on",
            "-c",
            "edit {0}".format(target),
        ],
        env=_nvim_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    try:
        _wait_for_socket(sock)
        _remote_send(nvim_path, sock, ":TaskmdClockStop<CR>")
        # Give the server a moment to actually reach the blocking
        # inputlist() prompt before answering it -- there is no
        # observable signal to poll on from outside the process
        # short of attaching an RPC client, so a short, generous
        # sleep is used instead (worked reliably at 0.3-0.5s by
        # hand; padded here for slower/loaded CI machines).
        time.sleep(0.6)
        _remote_send(nvim_path, sock, "{0}<CR>".format(choice))
        time.sleep(0.6)
        _remote_send(nvim_path, sock, ":qa!<CR>")
        proc.wait(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
    assert proc.returncode == 0, (
        proc.stdout and proc.stdout.read(),
        proc.stderr and proc.stderr.read(),
    )


def _tomorrow(offset_days: int = 1) -> datetime.date:
    """A near-future date, used to build synthetic `EVENT` fixtures
    that fall inside `taskmd schedule`'s default "today through 14
    days ahead" window regardless of what day the suite runs on."""
    return datetime.date.today() + datetime.timedelta(days=offset_days)


# ---------------------------------------------------------------------------
# :TaskmdClockStart / :TaskmdClockStop / :TaskmdClockStatus
# ---------------------------------------------------------------------------


def test_clock_start_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    target = tmp_path / "notes.task.md"
    target.write_text("# TODO Something :x:\n")
    _run_nvim_batch(nvim_path, target, ["TaskmdClockStart"], cursor_line=1)
    assert "CLOCK:" in target.read_text()


def test_clock_stop_single_open_via_real_nvim(
    nvim_path: pathlib.Path,
    tmp_path: pathlib.Path,
) -> None:
    # `clocked.task.md` has exactly one unclosed `CLOCK:` entry (on
    # "Write the parser"), so `:TaskmdClockStop` should resolve and
    # close it directly, with no ambiguity prompt involved.
    target = _copy_fixture("clocked.task.md", tmp_path)
    before = target.read_text()
    assert "2025-06-11T09:00:00+02:00]--" in before
    assert "2025-06-11T09:00:00+02:00]-- Continuing stage 2" in before

    _run_nvim_batch(nvim_path, target, ["TaskmdClockStop"])

    after = target.read_text()
    # The previously-open session now has a closing timestamp.
    assert "2025-06-11T09:00:00+02:00]--[" in after
    assert "Continuing stage 2" in after
    # Every other CLOCK: entry is untouched.
    assert "2025-06-09T09:15:00+02:00]--[2025-06-09T11:00:00+02:00]" in after
    assert "2025-06-10T09:00:00+02:00]--[2025-06-10T12:30:00+02:00]" in after
    assert "2025-06-05T13:00:00+02:00]--[2025-06-05T14:30:00+02:00]" in after


def test_clock_stop_ambiguous_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    target = _write_task_file(
        tmp_path,
        "ambiguous.task.md",
        "# TODO Task A :x:\n"
        "### CLOCK: [2025-01-01T09:00:00+00:00]--\n"
        "Working on A.\n"
        "\n"
        "# TODO Task B :x:\n"
        "### CLOCK: [2025-01-01T10:00:00+00:00]--\n"
        "Working on B.\n",
    )

    _run_ambiguous_stop(nvim_path, target, tmp_path, choice=2)

    after = target.read_text()
    # Task A's session (offered as choice 1) is still open.
    assert "[2025-01-01T09:00:00+00:00]--\n" in after
    # Task B's session (choice 2) got closed.
    assert "[2025-01-01T10:00:00+00:00]--[" in after


def test_clock_status_open_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    target = _copy_fixture("clocked.task.md", tmp_path)
    # Line 9 sits in the body of a *closed* CLOCK: entry, but it's
    # still within the "Write the parser" task overall, and that
    # task has a separate, still-open session -- status is per-task,
    # not per-clock-entry.
    echoed = _run_and_capture_echo(
        nvim_path, target, "TaskmdClockStatus", tmp_path, cursor_line=9
    )
    assert "taskmd: open" in echoed


def test_clock_status_closed_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    target = _copy_fixture("clocked.task.md", tmp_path)
    # Line 16 is in "Add logging", whose only CLOCK: entry is closed.
    echoed = _run_and_capture_echo(
        nvim_path, target, "TaskmdClockStatus", tmp_path, cursor_line=16
    )
    assert "taskmd: closed" in echoed


# ---------------------------------------------------------------------------
# :TaskmdReport / :TaskmdReportDir / :TaskmdListOpen
# ---------------------------------------------------------------------------


def test_report_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    target = _copy_fixture("basic.task.md", tmp_path)
    lines = _run_and_dump_buffer(nvim_path, target, "TaskmdReport", tmp_path)
    text = "\n".join(lines)
    assert "Write the parser" in text
    assert "Add logging" in text
    assert "Grand total" in text


def test_report_dir_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    _copy_fixture("basic.task.md", tmp_path)
    _copy_fixture("clocked.task.md", tmp_path)
    # `:TaskmdReportDir` reports on the *current buffer's* directory,
    # so any file inside `tmp_path` can be the one that's `edit`ed.
    target = tmp_path / "basic.task.md"
    lines = _run_and_dump_buffer(
        nvim_path, target, "TaskmdReportDir", tmp_path
    )
    text = "\n".join(lines)
    assert "basic.task.md" in text
    assert "clocked.task.md" in text
    assert "Grand total (all files)" in text


def test_list_open_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    target = _copy_fixture("clocked.task.md", tmp_path)
    lines = _run_and_dump_quickfix(
        nvim_path, target, "TaskmdListOpen", tmp_path
    )
    text = "\n".join(lines)
    assert "Write the parser" in text
    assert "Continuing stage 2" in text


# ---------------------------------------------------------------------------
# :TaskmdScheduleShow / :TaskmdScheduleConflicts / :TaskmdScheduleSummary
# ---------------------------------------------------------------------------


def test_schedule_show_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    target = _copy_fixture("scheduled.task.md", tmp_path)
    lines = _run_and_dump_buffer(
        nvim_path, target, "TaskmdScheduleShow", tmp_path
    )
    text = "\n".join(lines)
    # The fixture's weekly-recurring event should show up as an
    # upcoming occurrence somewhere in the default 14-day window,
    # however far in the future the anchor date has receded by the
    # time this test runs.
    assert "Focus session: parser work" in text
    assert "(recurring)" in text


def test_schedule_conflicts_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    day = _tomorrow().isoformat()
    target = _write_task_file(
        tmp_path,
        "conflicts.task.md",
        "# TODO Meetings :core:\n\n"
        "## EVENT [{0}T10:00:00+00:00--{0}T11:00:00+00:00] "
        "Sprint planning :meeting:\n\n"
        "## EVENT [{0}T10:30:00+00:00--{0}T11:30:00+00:00] "
        "Design review :meeting:\n".format(day),
    )
    lines = _run_and_dump_quickfix(
        nvim_path, target, "TaskmdScheduleConflicts", tmp_path
    )
    text = "\n".join(lines)
    assert "Sprint planning" in text
    assert "Design review" in text
    assert "overlaps" in text


def test_schedule_summary_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    target = _copy_fixture("scheduled.task.md", tmp_path)
    lines = _run_and_dump_buffer(
        nvim_path, target, "TaskmdScheduleSummary", tmp_path
    )
    text = "\n".join(lines)
    assert "block:" in text
    assert "Total:" in text


# ---------------------------------------------------------------------------
# Filetype detection (vim/ftdetect/taskmd.vim)
# ---------------------------------------------------------------------------


def _detected_filetype(
    nvim_path: pathlib.Path, target: pathlib.Path, tmp_path: pathlib.Path
) -> str:
    out_path = tmp_path / "filetype_dump.txt"
    _run_nvim_batch(
        nvim_path,
        target,
        [
            "redir! > {0}".format(out_path),
            "echo &filetype",
            "redir END",
        ],
    )
    return out_path.read_text().strip()


def test_ftdetect_task_md_extension_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    target = _write_task_file(
        tmp_path, "notes.task.md", "# TODO Something :x:\n"
    )
    assert _detected_filetype(nvim_path, target, tmp_path) == "taskmd"


def test_ftdetect_magic_comment_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    target = _write_task_file(
        tmp_path,
        "notes.md",
        "<!-- taskmd -->\n# TODO Something :x:\n",
    )
    assert _detected_filetype(nvim_path, target, tmp_path) == "taskmd"


def test_ftdetect_plain_md_is_not_taskmd_via_real_nvim(
    nvim_path: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    # A plain `.md` file without the magic first-line comment should
    # fall back to ordinary Markdown -- the whole point of the
    # `.task.md`/magic-comment scheme (SPEC.md, section 1.6) is that
    # unrelated `.md` files are left alone.
    target = _write_task_file(
        tmp_path, "notes.md", "# Just a regular markdown file\n"
    )
    assert _detected_filetype(nvim_path, target, tmp_path) == "markdown"
