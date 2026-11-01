#!/usr/bin/env python3
"""Drive real ncurses on a pseudo-terminal for the input loop.

Assumption tests check the ncurses behaviour the input selector
relies on. End-to-end tests play the cases stored as JSON files in
``input_input_loop_pty/TestRunEndToEnd.test_case``, through
``input_loop``'s layers: steps type text, optionally paced in seconds
between characters, sleep, resize the terminal, or expect lines
reported by the child, which names each key with ``curses.keyname``.
"""

# TODO(T-032): drop with the EventLoop tests, which these repeat.
# pylint: disable=duplicate-code

# Standard libraries.
import importlib.util
import json
import os
import pathlib
import selectors
import struct
import subprocess
import sys
import threading
import time

from typing import Any, Dict, Iterator, List

# External dependencies.
import pytest

if sys.platform == "win32":
    pytest.skip("pseudo-terminals are Unix-only", allow_module_level=True)

# Standard libraries, Unix-only.
# pylint: disable=wrong-import-order
import fcntl
import pty
import termios

# pylint: enable=wrong-import-order

pytestmark = pytest.mark.integration

# Run first in every child: take the terminal and open the report pipe.
PRELUDE = r"""
import asyncio, curses, fcntl, json, os, select, signal, sys, termios
import threading, time

fcntl.ioctl(0, termios.TIOCSCTTY, 0)
report = os.fdopen(int(sys.argv[1]), "w", buffering=1)
"""

# Reports each key by name, one per line. Every key redraws the whole
# screen, so keys also arrive during output.
# t: a thread wakes the loop. u: a task pushes back U while getch waits.
# w: sleeps with typeahead unread, reporting whether the loop spun.
APPLICATION = r"""
from bonipy35 import asyncio_ext
from bonipy35.curses_ext.input_loop import EventLoop, WindowInput, initialise

async def push_back():
    await asyncio.sleep(0.05)
    curses.ungetch(ord("U"))

async def app(window):
    loop = asyncio.get_event_loop()
    window_input = WindowInput(window)
    tasks = []
    count = 0
    report.write("ready\n")
    while True:
        key = await window_input.getch()
        name = curses.keyname(key).decode()
        if key == curses.KEY_RESIZE:
            report.write("%s %d %d\n" % ((name,) + window.getmaxyx()))
            continue
        if key == ord("q"):
            return
        if key == ord("t"):
            threading.Timer(
                0.05, loop.call_soon_threadsafe, [report.write, "woken\n"]
            ).start()
            continue
        if key == ord("u"):
            tasks.append(loop.create_task(push_back()))
            continue
        if key == ord("w"):
            start = time.process_time()
            await asyncio.sleep(0.3)
            spent = time.process_time() - start
            report.write("idle\n" if spent < 0.1 else "busy\n")
            continue
        count += 1
        height, width = window.getmaxyx()
        window.erase()
        for row in range(height - 1):
            window.addnstr(row, 0, "%d keys, last %s " % (count, name) * 9, width - 1)
        window.refresh()
        report.write(name + "\n")

with initialise() as window:
    asyncio_ext.run(app(window), loop_factory=EventLoop)
"""

TIMEOUT = 5


def set_size(fd: int, lines: int, columns: int) -> None:
    fcntl.ioctl(
        fd, termios.TIOCSWINSZ, struct.pack("HHHH", lines, columns, 0, 0)
    )


class Child:
    """Run ``script`` after `PRELUDE` on a new pseudo-terminal."""

    def __init__(self, script: str) -> None:
        self.master, slave = pty.openpty()
        set_size(self.master, 24, 80)
        self._report, report_writer = os.pipe()
        environment = dict(os.environ, TERM="xterm", ESCDELAY="100")
        try:
            # pylint: disable-next=consider-using-with
            self.process = subprocess.Popen(
                [sys.executable, "-c", PRELUDE + script, str(report_writer)],
                stdin=slave,
                stdout=slave,
                stderr=subprocess.PIPE,
                pass_fds=[report_writer],
                start_new_session=True,
                env=environment,
            )
        finally:
            os.close(slave)
            os.close(report_writer)
        self._buffer = b""
        # Drain the screen output so that the child never blocks on it.
        self._drainer = threading.Thread(target=self._drain)
        self._drainer.start()

    def _drain(self) -> None:
        try:
            while os.read(self.master, 65536):
                pass
        except OSError:
            # The child closed the terminal.
            pass

    def type(self, text: str, pace: float = 0) -> None:
        if not pace:
            os.write(self.master, text.encode())
            return
        for character in text:
            os.write(self.master, character.encode())
            time.sleep(pace)

    def read_lines(self, count: int) -> List[str]:
        deadline = time.monotonic() + TIMEOUT
        with selectors.DefaultSelector() as selector:
            selector.register(self._report, selectors.EVENT_READ)
            while self._buffer.count(b"\n") < count:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    break
                data = os.read(self._report, 65536)
                if not data:
                    break
                self._buffer += data
        *lines, self._buffer = self._buffer.split(b"\n")
        assert len(lines) == count, lines
        return [line.decode() for line in lines]

    def read_json(self) -> Any:
        return json.loads(self.read_lines(1)[0])

    def close(self) -> str:
        try:
            _output, error = self.process.communicate(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            self.process.kill()
            _output, error = self.process.communicate(timeout=TIMEOUT)
        os.close(self.master)
        self._drainer.join(timeout=TIMEOUT)
        os.close(self._report)
        return error.decode(errors="replace")


@pytest.fixture(name="ncurses", scope="module")
def fixture_ncurses() -> None:
    if importlib.util.find_spec("_curses") is None:
        pytest.skip("Python has no curses module")


@pytest.fixture(name="spawn")
def fixture_spawn(ncurses: None) -> Iterator[Any]:
    """Return a function starting a child, checked to exit cleanly."""
    del ncurses
    children = []  # type: List[Child]

    def spawn(script: str) -> Child:
        children.append(Child(script))
        return children[-1]

    yield spawn
    for child in children:
        error = child.close()
        assert child.process.returncode == 0, error


class TestNcursesAssumptions:
    def test_ungetch_does_not_show_on_input_fd(self, spawn: Any) -> None:
        child = spawn(r"""
window = curses.initscr()
window.nodelay(True)
curses.ungetch(ord("z"))
readable = bool(select.select([0], [], [], 0)[0])
key = window.getch()
curses.endwin()
report.write(json.dumps([readable, key]) + "\n")
""")
        assert child.read_json() == [False, ord("z")]

    def test_nodelay_getch_without_input_returns_at_once(
        self, spawn: Any
    ) -> None:
        child = spawn(r"""
window = curses.initscr()
window.nodelay(True)
start = time.monotonic()
key = window.getch()
elapsed = time.monotonic() - start
curses.endwin()
report.write(json.dumps([key, elapsed < 0.05]) + "\n")
""")
        assert child.read_json() == [-1, True]

    def test_typed_key_shows_on_input_fd(self, spawn: Any) -> None:
        child = spawn(r"""
window = curses.initscr()
window.nodelay(True)
report.write("ready\n")
readable = bool(select.select([0], [], [], 5)[0])
key = window.getch()
curses.endwin()
report.write(json.dumps([readable, key]) + "\n")
""")
        assert child.read_lines(1) == ["ready"]
        child.type("k")
        assert child.read_json() == [True, ord("k")]

    def test_resizeterm_queues_key_resize(self, spawn: Any) -> None:
        child = spawn(r"""
window = curses.initscr()
window.nodelay(True)
curses.resizeterm(30, 100)
key = curses.keyname(window.getch()).decode()
size = window.getmaxyx()
curses.endwin()
report.write(json.dumps([key, size]) + "\n")
""")
        assert child.read_json() == ["KEY_RESIZE", [30, 100]]

    def test_initscr_keeps_python_sigwinch_handler(self, spawn: Any) -> None:
        child = spawn(r"""
called = []
signal.signal(signal.SIGWINCH, lambda signum, frame: called.append(signum))
curses.initscr()
os.kill(os.getpid(), signal.SIGWINCH)
curses.endwin()
report.write(json.dumps(bool(called)) + "\n")
""")
        assert child.read_json() is True

    def test_isendwin_raises_before_initscr(self, spawn: Any) -> None:
        child = spawn(r"""
try:
    curses.isendwin()
except curses.error:
    raised = True
else:
    raised = False
report.write(json.dumps(raised) + "\n")
""")
        assert child.read_json() is True

    def test_isendwin_after_endwin(self, spawn: Any) -> None:
        child = spawn(r"""
curses.initscr()
before = curses.isendwin()
curses.endwin()
report.write(json.dumps([before, curses.isendwin()]) + "\n")
""")
        assert child.read_json() == [False, True]

    def test_initscr_again_returns_stdscr(self, spawn: Any) -> None:
        child = spawn(r"""
first = curses.initscr()
first.nodelay(True)
first.addstr(0, 0, "abc")
curses.ungetch(ord("z"))
second = curses.initscr()
text = second.instr(0, 0, 3).decode()
# Same window: nodelay and pushed back keys carry over.
keys = [second.getch(), second.getch()]
ended = curses.isendwin()
curses.endwin()
report.write(json.dumps([text, keys, ended]) + "\n")
""")
        assert child.read_json() == ["abc", [ord("z"), -1], False]


def play(child: Child, steps: List[Dict[str, Any]]) -> None:
    for step in steps:
        if "type" in step:
            child.type(step["type"], step.get("pace", 0))
        elif "sleep" in step:
            time.sleep(step["sleep"])
        elif "resize" in step:
            set_size(child.master, *step["resize"])
        elif "expect" in step:
            assert child.read_lines(len(step["expect"])) == step["expect"]
        else:
            raise ValueError("unknown step: {!r}".format(step))


@pytest.mark.e2e
class TestRunEndToEnd:
    def test_case(self, input_path: pathlib.Path, spawn: Any) -> None:
        case = json.loads(input_path.read_text(encoding="utf-8"))
        child = spawn(APPLICATION)
        assert child.read_lines(1) == ["ready"]
        play(child, case["steps"])
        child.type("q")
