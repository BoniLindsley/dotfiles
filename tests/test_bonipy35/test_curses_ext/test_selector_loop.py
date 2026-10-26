#!/usr/bin/env python3

# Shares code with asyncio_loop, the loop this one is meant to replace.
# pylint: disable=duplicate-code

# Standard libraries.
import asyncio
import collections
import contextlib
import curses
import os
import select
import selectors
import signal
import socket
import sys
import threading
import typing

from typing import Dict, Iterator, List, Optional
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext import selector_loop
from bonipy35.curses_ext.selector_loop import (
    EventLoop,
    _ConsoleSelector,
    EventLoopPolicy,
    keep_resize_handler,
    run,
    use_event_loop_policy,
)

WINDOWS = sys.platform == "win32"
needs_sigwinch = pytest.mark.skipif(
    not hasattr(signal, "SIGWINCH"), reason="no SIGWINCH"
)


class Terminal:
    """Stand in for ncurses reading stdin a byte at a time.

    Keys typed are bytes on ``input_socket``; keys queued inside curses,
    such as pushed back keys, never show on it.
    """

    def __init__(self, window: Mock) -> None:
        self.input_socket, self.keyboard = socket.socketpair()
        self.input_socket.setblocking(False)
        self.queued = collections.deque()  # type: collections.deque[int]
        self.reads = 0
        window.getch.side_effect = self.getch

    def getch(self) -> int:
        self.reads += 1
        if self.queued:
            return self.queued.popleft()
        try:
            data = self.input_socket.recv(1)
        except BlockingIOError:
            return -1
        return data[0] if data else -1

    def type(self, keys: bytes) -> None:
        self.keyboard.sendall(keys)

    def close(self) -> None:
        self.input_socket.close()
        self.keyboard.close()


class FakeConsole:
    """Stand in for the Windows console, waiting with ``select``.

    The terminal's input socket plays the console input handle;
    bound descriptors play sockets bound to the console's event.
    """

    def __init__(self, terminal: Terminal) -> None:
        self.input_socket = terminal.input_socket
        self.bound = {}  # type: Dict[int, int]
        self.resets = 0
        self.waits = []  # type: List[Optional[float]]
        self.closed = False

    def bind(self, fd: int, events: int) -> None:
        self.bound[fd] = events

    def unbind(self, fd: int) -> None:
        del self.bound[fd]

    def reset(self) -> None:
        self.resets += 1

    def wait(self, timeout: Optional[float]) -> None:
        self.waits.append(timeout)
        select.select(
            [self.input_socket]
            + [fd for fd, events in self.bound.items() if events & 1],
            [fd for fd, events in self.bound.items() if events & 2],
            [],
            timeout,
        )

    def close(self) -> None:
        self.closed = True


@pytest.fixture(name="terminal")
def fixture_terminal(window: Mock) -> Iterator[Terminal]:
    terminal = Terminal(window)
    try:
        yield terminal
    finally:
        terminal.close()


@contextlib.contextmanager
def make_loop(window: Mock, terminal: Terminal) -> Iterator[EventLoop]:
    loop = EventLoop(stdscr=window, input_fd=terminal.input_socket.fileno())
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(name="windows_console")
def fixture_windows_console(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Make the loop's real Windows consoles wait on an unsignalled event.

    Mock windows read no console events, so events pending on the real
    console input, such as releasing Enter after starting the tests,
    would keep it signalled and the loop from ever waiting.
    """
    if sys.platform != "win32":
        pytest.skip("needs Windows")
    # pylint: disable-next=import-outside-toplevel
    import ctypes
    from ctypes import wintypes  # pylint: disable=import-outside-toplevel

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateEventW.restype = wintypes.HANDLE
    kernel32.CreateEventW.argtypes = [
        wintypes.LPVOID,
        wintypes.BOOL,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    event = kernel32.CreateEventW(None, True, False, None)
    assert event
    monkeypatch.setattr(
        selector_loop,
        "_new_console",
        # pylint: disable-next=protected-access
        lambda: selector_loop._Console(console_input=event),
    )
    try:
        yield
    finally:
        kernel32.CloseHandle(event)


@pytest.fixture(
    name="wait",
    params=(
        ["fake-console", "windows-console"]
        if WINDOWS
        else ["descriptors", "fake-console"]
    ),
)
def fixture_wait(
    request: pytest.FixtureRequest,
    terminal: Terminal,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    """Wait on descriptors, a fake console, or the real Windows console.

    Keys typed on the terminal reach the loop in each case,
    since the tests type them before the loop checks for keys.
    """
    if request.param == "descriptors":
        monkeypatch.setattr(selector_loop, "_new_console", lambda: None)
    elif request.param == "fake-console":
        console = FakeConsole(terminal)
        monkeypatch.setattr(selector_loop, "_new_console", lambda: console)
    else:
        request.getfixturevalue("windows_console")
    return typing.cast(str, request.param)


@pytest.fixture(name="loop")
def fixture_loop(
    window: Mock, terminal: Terminal, wait: str
) -> Iterator[EventLoop]:
    del wait
    with make_loop(window, terminal) as loop:
        yield loop


@pytest.fixture(name="descriptor_loop")
def fixture_descriptor_loop(
    window: Mock, terminal: Terminal, monkeypatch: pytest.MonkeyPatch
) -> Iterator[EventLoop]:
    if WINDOWS:
        pytest.skip("Windows waits on the console")
    monkeypatch.setattr(selector_loop, "_new_console", lambda: None)
    with make_loop(window, terminal) as loop:
        yield loop


@pytest.fixture(name="console_loop")
def fixture_console_loop(
    window: Mock, terminal: Terminal, monkeypatch: pytest.MonkeyPatch
) -> Iterator[EventLoop]:
    console = FakeConsole(terminal)
    monkeypatch.setattr(selector_loop, "_new_console", lambda: console)
    with make_loop(window, terminal) as loop:
        yield loop


@pytest.fixture(name="stdin")
def fixture_stdin(
    request: pytest.FixtureRequest, terminal: Terminal
) -> Iterator[Terminal]:
    """Put the terminal's input on file descriptor 0 for ``run``."""
    if WINDOWS:
        # The loop waits on the console there, not on descriptor 0.
        request.getfixturevalue("windows_console")
        yield terminal
        return
    saved = os.dup(0)
    os.dup2(terminal.input_socket.fileno(), 0)
    try:
        yield terminal
    finally:
        os.dup2(saved, 0)
        os.close(saved)


class TestEventLoop:
    def test_nodelay(self, loop: EventLoop, window: Mock) -> None:
        window.nodelay.assert_called_once_with(True)
        assert loop.window is window

    def test_keys_fifo(self, loop: EventLoop, terminal: Terminal) -> None:
        async def check() -> List[int]:
            first = loop.create_task(loop.getch())
            second = loop.create_task(loop.getch())
            await asyncio.sleep(0)
            terminal.type(b"ab")
            return [await first, await second]

        assert loop.run_until_complete(asyncio.wait_for(check(), 1)) == [
            ord("a"),
            ord("b"),
        ]

    def test_cancel_preserves_key(
        self, loop: EventLoop, terminal: Terminal
    ) -> None:
        async def check() -> int:
            task = loop.create_task(loop.getch())
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            terminal.type(b"x")
            return await loop.getch()

        assert loop.run_until_complete(asyncio.wait_for(check(), 1)) == ord(
            "x"
        )

    def test_cancelled_waiter(
        self, loop: EventLoop, terminal: Terminal
    ) -> None:
        waiter = loop.create_future()
        waiter.cancel()
        loop._input_waiters.append(waiter)  # pylint: disable=protected-access
        terminal.type(b"k")
        loop.run_until_complete(asyncio.sleep(0))
        assert loop.run_until_complete(loop.getch()) == ord("k")

    def test_buffered_keys(self, loop: EventLoop, terminal: Terminal) -> None:
        terminal.type(b"12")
        loop.run_until_complete(asyncio.sleep(0))
        assert loop.run_until_complete(loop.getch()) == ord("1")
        assert loop.run_until_complete(loop.getch()) == ord("2")

    def test_queued_key_before_wait(
        self, loop: EventLoop, terminal: Terminal
    ) -> None:
        # Nothing arrives on the input; only curses' queue holds a key,
        # as after ungetch.
        terminal.queued.append(ord("u"))
        assert loop.run_until_complete(
            asyncio.wait_for(loop.getch(), 1)
        ) == ord("u")

    def test_queued_key_with_timer(
        self, loop: EventLoop, terminal: Terminal
    ) -> None:
        async def check() -> int:
            task = loop.create_task(loop.getch())
            await asyncio.sleep(0)
            terminal.queued.append(ord("q"))
            # The waiter gets the key without waiting for this timer.
            loop.call_later(10, lambda: None)
            return await task

        assert loop.run_until_complete(asyncio.wait_for(check(), 1)) == ord(
            "q"
        )

    def test_thread_wakeup(self, loop: EventLoop) -> None:
        ready = loop.create_future()
        started = threading.Event()

        def worker() -> None:
            assert started.wait(1)
            loop.call_soon_threadsafe(ready.set_result, 42)

        thread = threading.Thread(target=worker)
        thread.start()
        try:
            loop.call_soon(started.set)
            assert loop.run_until_complete(asyncio.wait_for(ready, 1)) == 42
        finally:
            thread.join(timeout=2)
        assert not thread.is_alive()

    @pytest.mark.skipif(WINDOWS, reason="Windows selects only sockets")
    def test_pipe_reader(self, loop: EventLoop) -> None:
        read_fd, write_fd = os.pipe()
        try:
            ready = loop.create_future()

            def read() -> None:
                loop.remove_reader(read_fd)
                ready.set_result(os.read(read_fd, 10))

            loop.add_reader(read_fd, read)
            loop.call_soon(os.write, write_fd, b"pipe")
            assert loop.run_until_complete(asyncio.wait_for(ready, 1)) == (
                b"pipe"
            )
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def test_reader_and_writer(self, loop: EventLoop) -> None:
        left, right = socket.socketpair()
        try:
            writable = loop.create_future()

            def write() -> None:
                loop.remove_writer(left.fileno())
                writable.set_result(True)

            loop.add_reader(left.fileno(), lambda: None)
            # Watching the same descriptor for writing modifies its key.
            loop.add_writer(left.fileno(), write)
            assert loop.run_until_complete(asyncio.wait_for(writable, 1))
            loop.remove_reader(left.fileno())
        finally:
            left.close()
            right.close()

    @pytest.mark.skipif(
        WINDOWS, reason="Windows selector loops run no subprocesses"
    )
    def test_subprocess(self, loop: EventLoop) -> None:
        async def check() -> bytes:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                "print('child')",
                stdout=asyncio.subprocess.PIPE,
            )
            output, _error = await process.communicate()
            return output

        assert loop.run_until_complete(asyncio.wait_for(check(), 10)) == (
            b"child" + os.linesep.encode()
        )

    def test_no_periodic_wakeups(
        self, loop: EventLoop, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # pylint: disable-next=protected-access
        selector = loop._selector  # type: ignore[attr-defined]
        # Consoles wait themselves; otherwise the wrapped selector waits.
        waiter, name = getattr(selector, "_console", None), "wait"
        if waiter is None:
            # pylint: disable-next=protected-access
            waiter, name = selector._selector, "select"
        wait = getattr(waiter, name)
        timeouts = []  # type: List[Optional[float]]

        def record(timeout: Optional[float] = None) -> typing.Any:
            timeouts.append(timeout)
            return wait(timeout)

        monkeypatch.setattr(waiter, name, record)
        loop.run_until_complete(asyncio.sleep(0.05))
        waits = [timeout for timeout in timeouts if timeout]
        # Timer resolution may add one short wait at the end.
        assert 1 <= len(waits) <= 2
        assert waits[0] >= 0.04

    def test_resize(
        self, descriptor_loop: EventLoop, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        loop = descriptor_loop
        resized = loop.create_future()
        monkeypatch.setattr(
            curses,
            "resizeterm",
            Mock(side_effect=lambda *size: resized.set_result(size)),
        )
        monkeypatch.setattr(
            os,
            "get_terminal_size",
            Mock(return_value=os.terminal_size((100, 30))),
        )
        loop.call_soon(os.kill, os.getpid(), signal.SIGWINCH)
        assert loop.run_until_complete(asyncio.wait_for(resized, 1)) == (
            30,
            100,
        )

    def test_resize_without_terminal(
        self, descriptor_loop: EventLoop, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        loop = descriptor_loop
        monkeypatch.setattr(curses, "resizeterm", Mock())
        monkeypatch.setattr(
            os, "get_terminal_size", Mock(side_effect=OSError)
        )
        loop._resize()  # pylint: disable=protected-access
        curses.resizeterm.assert_not_called()  # type: ignore[attr-defined]

    @needs_sigwinch
    def test_without_sigwinch(
        self,
        window: Mock,
        terminal: Terminal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(selector_loop, "_new_console", lambda: None)
        monkeypatch.delattr(signal, "SIGWINCH")
        loop = EventLoop(
            stdscr=window, input_fd=terminal.input_socket.fileno()
        )
        try:
            assert not loop._signal_handlers  # type: ignore[attr-defined]  # pylint: disable=protected-access
        finally:
            loop.close()

    def test_input_error(
        self, loop: EventLoop, window: Mock, terminal: Terminal
    ) -> None:
        window.getch.side_effect = curses.error("failed")
        with pytest.raises(curses.error):
            loop.run_until_complete(asyncio.sleep(0))
        window.getch.side_effect = terminal.getch
        # Finish the task left pending when reading input failed.
        for task in asyncio.all_tasks(loop):
            loop.run_until_complete(task)

    def test_close(
        self, loop: EventLoop, window: Mock, terminal: Terminal
    ) -> None:
        waiter = loop.create_future()
        loop._input_waiters.append(waiter)  # pylint: disable=protected-access
        loop.close()
        loop.close()
        assert waiter.cancelled()
        window.nodelay.assert_called_with(False)
        # The input is no longer watched.
        terminal.type(b"z")
        with pytest.raises(RuntimeError, match="closed"):
            asyncio.run(loop.getch())

    def test_close_signal(self, descriptor_loop: EventLoop) -> None:
        descriptor_loop.close()
        assert signal.getsignal(signal.SIGWINCH) == signal.SIG_DFL

    def test_wrong_loop(self, loop: EventLoop) -> None:
        other = asyncio.new_event_loop()
        try:
            with pytest.raises(RuntimeError, match="owning"):
                other.run_until_complete(loop.getch())
        finally:
            other.close()

    def test_close_running(self, loop: EventLoop) -> None:
        async def check() -> None:
            with pytest.raises(RuntimeError, match="running"):
                loop.close()

        loop.run_until_complete(check())


class TestConsoleSelector:
    def test_input_not_registered(
        self, console_loop: EventLoop, terminal: Terminal
    ) -> None:
        # pylint: disable-next=protected-access
        selector = console_loop._selector  # type: ignore[attr-defined]
        assert terminal.input_socket.fileno() not in selector.get_map()
        # Only asyncio's own wakeup socket.
        assert len(selector.get_map()) == 1

    def test_ready_without_waiting(
        self, console_loop: EventLoop, terminal: Terminal
    ) -> None:
        console = FakeConsole(terminal)
        selector = _ConsoleSelector(
            selectors.DefaultSelector(), console_loop, console
        )
        left, right = socket.socketpair()
        try:
            selector.register(left, selectors.EVENT_READ)
            right.sendall(b"x")
            # Ready before waiting, as a socket whose network event
            # was already signalled would be.
            assert [key.fileobj for key, _events in selector.select()] == [
                left
            ]
            left.recv(1)
            terminal.queued.append(ord("k"))
            # A key read before waiting also returns at once.
            assert not selector.select()
            assert not console.waits
            assert console.resets == 2
            assert console_loop.run_until_complete(console_loop.getch()) == (
                ord("k")
            )
            selector.unregister(left)
            assert not console.bound
        finally:
            selector.close()
            left.close()
            right.close()
        assert console.closed

    def test_zero_timeout(self, console_loop: EventLoop) -> None:
        # pylint: disable-next=protected-access
        selector = console_loop._selector  # type: ignore[attr-defined]
        assert not selector.select(0)
        assert not selector._console.waits  # pylint: disable=protected-access

    def test_binding(self, console_loop: EventLoop) -> None:
        # pylint: disable-next=protected-access
        selector = console_loop._selector  # type: ignore[attr-defined]
        console = selector._console  # pylint: disable=protected-access
        left, right = socket.socketpair()
        try:
            console_loop.add_reader(left.fileno(), lambda: None)
            assert console.bound[left.fileno()] == selectors.EVENT_READ
            console_loop.add_writer(left.fileno(), lambda: None)
            assert console.bound[left.fileno()] == (
                selectors.EVENT_READ | selectors.EVENT_WRITE
            )
            console_loop.remove_reader(left.fileno())
            console_loop.remove_writer(left.fileno())
            assert left.fileno() not in console.bound
        finally:
            left.close()
            right.close()

    def test_bind_failure(
        self, console_loop: EventLoop, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # pylint: disable-next=protected-access
        selector = console_loop._selector  # type: ignore[attr-defined]
        console = selector._console  # pylint: disable=protected-access
        monkeypatch.setattr(console, "bind", Mock(side_effect=OSError))
        left, right = socket.socketpair()
        try:
            with pytest.raises(OSError):
                console_loop.add_reader(left.fileno(), lambda: None)
            assert left.fileno() not in selector.get_map()
        finally:
            left.close()
            right.close()

    def test_resize(
        self,
        console_loop: EventLoop,
        terminal: Terminal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(curses, "resize_term", Mock())
        terminal.queued.append(curses.KEY_RESIZE)
        assert console_loop.run_until_complete(console_loop.getch()) == (
            curses.KEY_RESIZE
        )
        curses.resize_term.assert_called_once_with(0, 0)  # type: ignore[attr-defined]

    def test_wakeup_fd(
        self,
        window: Mock,
        terminal: Terminal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        console = FakeConsole(terminal)
        monkeypatch.setattr(selector_loop, "_new_console", lambda: console)
        previous = signal.set_wakeup_fd(-1)
        signal.set_wakeup_fd(previous)
        with make_loop(window, terminal) as loop:
            current = signal.set_wakeup_fd(-1)
            signal.set_wakeup_fd(current)
            # pylint: disable-next=protected-access
            assert current == loop._csock.fileno()  # type: ignore[attr-defined]
        assert signal.set_wakeup_fd(previous) == previous
        assert console.closed


class TestKeepResizeHandler:
    @needs_sigwinch
    def test_restores(self) -> None:
        previous = signal.getsignal(signal.SIGWINCH)
        with keep_resize_handler():
            # A Python handler, so ncurses does not install its own.
            assert callable(signal.getsignal(signal.SIGWINCH))
            os.kill(os.getpid(), signal.SIGWINCH)
        assert signal.getsignal(signal.SIGWINCH) == previous

    @needs_sigwinch
    def test_unknown_previous(self, monkeypatch: pytest.MonkeyPatch) -> None:
        handlers = []

        # Handlers installed outside Python are reported as None.
        def set_handler(signum: int, handler: typing.Any) -> None:
            assert signum == signal.SIGWINCH
            handlers.append(handler)

        monkeypatch.setattr(signal, "signal", set_handler)
        with keep_resize_handler():
            pass
        assert handlers[-1] == signal.SIG_DFL

    def test_without_sigwinch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(signal, "SIGWINCH", raising=False)
        monkeypatch.setattr(signal, "signal", Mock())
        with keep_resize_handler():
            pass
        signal.signal.assert_not_called()  # type: ignore[attr-defined]


class TestPolicy:
    @pytest.mark.parametrize("fail", [False, True])
    def test_restores(self, window: Mock, fail: bool) -> None:
        previous = asyncio.get_event_loop_policy()
        try:
            with use_event_loop_policy(window) as policy:
                assert isinstance(policy, EventLoopPolicy)
                assert asyncio.get_event_loop_policy() is policy
                if fail:
                    raise ValueError()
        except ValueError:
            pass
        assert asyncio.get_event_loop_policy() is previous

    def test_new_event_loop(self, window: Mock, stdin: Terminal) -> None:
        del stdin
        loop = EventLoopPolicy(stdscr=window).new_event_loop()
        try:
            assert isinstance(loop, EventLoop)
            assert loop.window is window
        finally:
            loop.close()


class TestRun:
    @pytest.fixture(autouse=True, params=[False, True])
    def fixture_runner(
        self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if request.param:
            monkeypatch.delattr(asyncio, "run")

    def test_reads_stdin(self, window: Mock, stdin: Terminal) -> None:
        async def app() -> int:
            loop = asyncio.get_event_loop()
            assert isinstance(loop, EventLoop)
            assert loop.window is window
            stdin.type(b"r")
            return await loop.getch()

        assert run(app()) == ord("r")
        assert run(app()) == ord("r")

    @needs_sigwinch
    def test_restores_resize_handler(
        self, window: Mock, stdin: Terminal
    ) -> None:
        del window, stdin

        async def app() -> None:
            pass

        previous = signal.getsignal(signal.SIGWINCH)
        run(app())
        assert signal.getsignal(signal.SIGWINCH) == previous

    def test_terminal_cleanup_on_failure(
        self, window: Mock, stdin: Terminal
    ) -> None:
        del stdin

        async def app() -> None:
            raise ValueError("application failed")

        with pytest.raises(ValueError, match="application failed"):
            run(app())
        window.keypad.assert_called_with(False)
        window.nodelay.assert_called_with(False)
        curses.endwin.assert_called_once()  # type: ignore[attr-defined]
