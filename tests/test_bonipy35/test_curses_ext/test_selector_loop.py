#!/usr/bin/env python3

# Shares code with asyncio_loop, the loop this one is meant to replace.
# pylint: disable=duplicate-code

# Standard libraries.
import asyncio
import collections
import curses
import os
import signal
import socket
import sys
import threading
import typing

from typing import Iterator, List, Optional
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext.selector_loop import (
    EventLoop,
    EventLoopPolicy,
    keep_resize_handler,
    run,
    use_event_loop_policy,
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


@pytest.fixture(name="terminal")
def fixture_terminal(window: Mock) -> Iterator[Terminal]:
    terminal = Terminal(window)
    try:
        yield terminal
    finally:
        terminal.close()


@pytest.fixture(name="loop")
def fixture_loop(window: Mock, terminal: Terminal) -> Iterator[EventLoop]:
    loop = EventLoop(stdscr=window, input_fd=terminal.input_socket.fileno())
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(name="stdin")
def fixture_stdin(terminal: Terminal) -> Iterator[Terminal]:
    """Put the terminal's input on file descriptor 0 for ``run``."""
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
        # Nothing arrives on the input; only curses' queue holds a key.
        terminal.queued.append(curses.KEY_RESIZE)
        assert (
            loop.run_until_complete(asyncio.wait_for(loop.getch(), 1))
            == curses.KEY_RESIZE
        )

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
        selector = loop._selector._selector  # type: ignore[attr-defined]
        select = selector.select
        timeouts = []  # type: List[Optional[float]]

        def record(timeout: Optional[float] = None) -> typing.Any:
            timeouts.append(timeout)
            return select(timeout)

        monkeypatch.setattr(selector, "select", record)
        loop.run_until_complete(asyncio.sleep(0.05))
        waits = [timeout for timeout in timeouts if timeout]
        # Timer resolution may add one short wait at the end.
        assert 1 <= len(waits) <= 2
        assert waits[0] >= 0.04

    def test_resize(
        self, loop: EventLoop, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        self, loop: EventLoop, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(curses, "resizeterm", Mock())
        monkeypatch.setattr(
            os, "get_terminal_size", Mock(side_effect=OSError)
        )
        loop._resize()  # pylint: disable=protected-access
        curses.resizeterm.assert_not_called()  # type: ignore[attr-defined]

    def test_without_sigwinch(
        self,
        window: Mock,
        terminal: Terminal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
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
        assert signal.getsignal(signal.SIGWINCH) == signal.SIG_DFL
        # The input is no longer watched.
        terminal.type(b"z")
        with pytest.raises(RuntimeError, match="closed"):
            asyncio.run(loop.getch())

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


class TestKeepResizeHandler:
    def test_restores(self) -> None:
        previous = signal.getsignal(signal.SIGWINCH)
        with keep_resize_handler():
            # A Python handler, so ncurses does not install its own.
            assert callable(signal.getsignal(signal.SIGWINCH))
            os.kill(os.getpid(), signal.SIGWINCH)
        assert signal.getsignal(signal.SIGWINCH) == previous

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
        monkeypatch.delattr(signal, "SIGWINCH")
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

        previous = signal.getsignal(signal.SIGWINCH)
        assert run(app()) == ord("r")
        assert run(app()) == ord("r")
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
