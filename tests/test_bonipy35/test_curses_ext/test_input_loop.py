#!/usr/bin/env python3
"""Unit tests of the input loop, with curses replaced by a fake terminal.

Real ncurses is driven on a pseudo-terminal in ``test_input_loop_pty``.
"""

# TODO(T-032): drop with the EventLoop tests, which these repeat.
# pylint: disable=duplicate-code

# Standard libraries.
import asyncio
import collections
import contextlib
import curses
import os
import selectors
import signal
import socket
import sys
import typing

from typing import Iterator, List
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35 import asyncio_ext
from bonipy35.curses_ext.input_loop import (
    EventLoop,
    InputSelector,
    InputWaiter,
    WindowInput,
    _resize,
    initialise,
    keep_resize_handler,
)

needs_sigwinch = pytest.mark.skipif(
    not hasattr(signal, "SIGWINCH"), reason="no SIGWINCH"
)
needs_unix = pytest.mark.skipif(
    sys.platform == "win32", reason="Windows selectors take sockets only"
)


class Terminal:
    """Stand in for ncurses reading a terminal a byte at a time.

    Keys typed are bytes on ``input_socket``.
    Keys pushed back with ``curses.ungetch`` are queued inside curses
    and never show on it.
    """

    def __init__(self, window: Mock, monkeypatch: pytest.MonkeyPatch) -> None:
        self.input_socket, self.keyboard = socket.socketpair()
        self.input_socket.setblocking(False)
        self.queued = collections.deque()  # type: collections.deque[int]
        self.reads = 0
        window.getch.side_effect = self.getch
        monkeypatch.setattr(curses, "ungetch", self.ungetch)

    @property
    def input_fd(self) -> int:
        return self.input_socket.fileno()

    def getch(self) -> int:
        self.reads += 1
        if self.queued:
            return self.queued.popleft()
        try:
            data = self.input_socket.recv(1)
        except BlockingIOError:
            return -1
        return data[0] if data else -1

    def ungetch(self, key: int) -> None:
        self.queued.appendleft(key)

    def type(self, keys: bytes) -> None:
        self.keyboard.sendall(keys)

    def close(self) -> None:
        self.input_socket.close()
        self.keyboard.close()


@pytest.fixture(name="terminal")
def fixture_terminal(
    window: Mock, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Terminal]:
    terminal = Terminal(window, monkeypatch)
    try:
        yield terminal
    finally:
        terminal.close()


@pytest.fixture(name="selector")
def fixture_selector(
    window: Mock, terminal: Terminal
) -> Iterator[InputSelector]:
    with InputSelector(window=window, input_fd=terminal.input_fd) as selector:
        yield selector


@pytest.fixture(name="loop")
def fixture_loop(
    selector: InputSelector,
) -> Iterator[asyncio.AbstractEventLoop]:
    with contextlib.closing(EventLoop(selector)) as loop:
        asyncio.set_event_loop(loop)
        try:
            yield loop
        finally:
            asyncio.set_event_loop(None)


@pytest.fixture(name="waiter")
def fixture_waiter(
    loop: asyncio.AbstractEventLoop, terminal: Terminal
) -> InputWaiter:
    return InputWaiter(loop, input_fd=terminal.input_fd)


@pytest.fixture(name="stdin")
def fixture_stdin(terminal: Terminal) -> Iterator[Terminal]:
    """Put the terminal's input on file descriptor 0 for ``run``."""
    saved = os.dup(0)
    os.dup2(terminal.input_fd, 0)
    try:
        yield terminal
    finally:
        os.dup2(saved, 0)
        os.close(saved)


def is_registered(selector: InputSelector, terminal: Terminal) -> bool:
    return terminal.input_fd in selector.get_map()


class TestInputSelectorMixin:
    def test_not_registered_does_not_peek(
        self, selector: InputSelector, terminal: Terminal
    ) -> None:
        terminal.queued.append(ord("a"))
        assert not selector.select(0)
        assert terminal.reads == 0

    def test_queued_key(
        self, selector: InputSelector, terminal: Terminal
    ) -> None:
        key = selector.register(terminal.input_fd, selectors.EVENT_READ)
        terminal.queued.append(ord("a"))
        # Would block forever if the queued key were missed.
        assert selector.select(None) == [(key, selectors.EVENT_READ)]
        assert list(terminal.queued) == [ord("a")]
        assert terminal.reads == 1

    def test_typed_and_queued_once(
        self, selector: InputSelector, terminal: Terminal
    ) -> None:
        key = selector.register(terminal.input_fd, selectors.EVENT_READ)
        terminal.queued.append(ord("a"))
        terminal.type(b"b")
        assert selector.select(None) == [(key, selectors.EVENT_READ)]

    def test_other_ready_kept(
        self, selector: InputSelector, terminal: Terminal
    ) -> None:
        reader, writer = socket.socketpair()
        with reader, writer:
            other = selector.register(reader, selectors.EVENT_READ)
            key = selector.register(terminal.input_fd, selectors.EVENT_READ)
            writer.sendall(b"x")
            terminal.queued.append(ord("a"))
            assert sorted(
                selector.select(None), key=lambda item: item[0].fd
            ) == sorted(
                [(other, selectors.EVENT_READ), (key, selectors.EVENT_READ)],
                key=lambda item: item[0].fd,
            )

    def test_waits_without_key(
        self, selector: InputSelector, terminal: Terminal
    ) -> None:
        key = selector.register(terminal.input_fd, selectors.EVENT_READ)
        assert not selector.select(0.01)
        assert terminal.reads == 1
        terminal.type(b"c")
        assert selector.select(None) == [(key, selectors.EVENT_READ)]

    def test_default_window_is_stdscr(
        self,
        window: Mock,
        terminal: Terminal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        del window
        monkeypatch.setattr(curses, "isendwin", Mock(return_value=False))
        with InputSelector(input_fd=terminal.input_fd) as selector:
            key = selector.register(terminal.input_fd, selectors.EVENT_READ)
            terminal.queued.append(ord("a"))
            assert selector.select(None) == [(key, selectors.EVENT_READ)]
        # Peeked through the window that initscr returned.
        assert terminal.reads == 1

    @pytest.mark.parametrize(
        "isendwin",
        [
            Mock(side_effect=curses.error("must call initscr() first")),
            Mock(return_value=True),
        ],
        ids=["before_initscr", "after_endwin"],
    )
    def test_default_window_without_curses(
        self, monkeypatch: pytest.MonkeyPatch, isendwin: Mock
    ) -> None:
        initscr = Mock()
        monkeypatch.setattr(curses, "initscr", initscr)
        monkeypatch.setattr(curses, "isendwin", isendwin)
        with pytest.raises(curses.error):
            InputSelector()
        initscr.assert_not_called()

    def test_write_only_not_peeked(
        self, selector: InputSelector, terminal: Terminal
    ) -> None:
        key = selector.register(terminal.input_fd, selectors.EVENT_WRITE)
        terminal.queued.append(ord("a"))
        assert selector.select(None) == [(key, selectors.EVENT_WRITE)]
        assert terminal.reads == 0


class TestInputWaiter:
    def test_wakes_for_typed_key(
        self,
        loop: asyncio.AbstractEventLoop,
        selector: InputSelector,
        terminal: Terminal,
        waiter: InputWaiter,
    ) -> None:
        loop.call_later(0.01, terminal.type, b"a")
        loop.run_until_complete(asyncio.wait_for(waiter.input_ready(), 5))
        assert not is_registered(selector, terminal)

    def test_wakes_for_key_queued_by_task(
        self,
        loop: asyncio.AbstractEventLoop,
        terminal: Terminal,
        waiter: InputWaiter,
    ) -> None:
        async def push_back() -> None:
            await asyncio.sleep(0.01)
            curses.ungetch(ord("u"))

        task = loop.create_task(push_back())
        loop.run_until_complete(asyncio.wait_for(waiter.input_ready(), 5))
        loop.run_until_complete(task)
        assert list(terminal.queued) == [ord("u")]

    def test_no_peek_while_not_waiting(
        self,
        loop: asyncio.AbstractEventLoop,
        terminal: Terminal,
        waiter: InputWaiter,
    ) -> None:
        terminal.queued.append(ord("a"))
        loop.run_until_complete(asyncio.sleep(0.02))
        assert terminal.reads == 0
        loop.run_until_complete(asyncio.wait_for(waiter.input_ready(), 5))
        reads = terminal.reads
        # The key stays unread, as during long work.
        loop.run_until_complete(asyncio.sleep(0.02))
        assert terminal.reads == reads

    def test_no_polling(
        self,
        loop: asyncio.AbstractEventLoop,
        selector: InputSelector,
        terminal: Terminal,
        waiter: InputWaiter,
    ) -> None:
        with pytest.raises(asyncio.TimeoutError):
            loop.run_until_complete(
                asyncio.wait_for(waiter.input_ready(), 0.1)
            )
        # One peek before the wait, maybe one more as the timer fires.
        assert terminal.reads <= 2
        assert not is_registered(selector, terminal)

    def test_shared_registration(
        self,
        loop: asyncio.AbstractEventLoop,
        selector: InputSelector,
        terminal: Terminal,
        waiter: InputWaiter,
    ) -> None:
        async def both() -> None:
            first = loop.create_task(waiter.input_ready())
            second = loop.create_task(waiter.input_ready())
            await asyncio.sleep(0.01)
            assert is_registered(selector, terminal)
            terminal.type(b"a")
            await asyncio.wait_for(asyncio.gather(first, second), 5)

        loop.run_until_complete(both())
        assert not is_registered(selector, terminal)

    def test_cancel_keeps_others(
        self,
        loop: asyncio.AbstractEventLoop,
        selector: InputSelector,
        terminal: Terminal,
        waiter: InputWaiter,
    ) -> None:
        async def cancel_one() -> None:
            first = loop.create_task(waiter.input_ready())
            second = loop.create_task(waiter.input_ready())
            await asyncio.sleep(0.01)
            first.cancel()
            await asyncio.gather(first, return_exceptions=True)
            assert is_registered(selector, terminal)
            terminal.type(b"a")
            await asyncio.wait_for(second, 5)

        loop.run_until_complete(cancel_one())
        assert not is_registered(selector, terminal)

    def test_cancel_last_unregisters(
        self,
        loop: asyncio.AbstractEventLoop,
        selector: InputSelector,
        terminal: Terminal,
        waiter: InputWaiter,
    ) -> None:
        async def cancel() -> None:
            task = loop.create_task(waiter.input_ready())
            await asyncio.sleep(0.01)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

        loop.run_until_complete(cancel())
        assert not is_registered(selector, terminal)

    def test_wake(
        self,
        loop: asyncio.AbstractEventLoop,
        selector: InputSelector,
        terminal: Terminal,
        waiter: InputWaiter,
    ) -> None:
        async def wake_both() -> None:
            first = loop.create_task(waiter.input_ready())
            second = loop.create_task(waiter.input_ready())
            await asyncio.sleep(0.01)
            waiter.wake()
            await asyncio.wait_for(asyncio.gather(first, second), 5)

        loop.run_until_complete(wake_both())
        assert not is_registered(selector, terminal)
        assert terminal.reads <= 2

    def test_wake_after_cancel(
        self,
        loop: asyncio.AbstractEventLoop,
        selector: InputSelector,
        terminal: Terminal,
        waiter: InputWaiter,
    ) -> None:
        async def cancel_then_wake() -> None:
            first = loop.create_task(waiter.input_ready())
            second = loop.create_task(waiter.input_ready())
            await asyncio.sleep(0.01)
            # Cancels the first future before its task cleans up.
            first.cancel()
            waiter.wake()
            await asyncio.gather(first, return_exceptions=True)
            await asyncio.wait_for(second, 5)
            assert first.cancelled()

        loop.run_until_complete(cancel_then_wake())
        assert not is_registered(selector, terminal)

    def test_wake_without_waiters(
        self,
        selector: InputSelector,
        terminal: Terminal,
        waiter: InputWaiter,
    ) -> None:
        waiter.wake()
        assert not is_registered(selector, terminal)


class TestWindowInput:
    def test_queued_key(
        self,
        loop: asyncio.AbstractEventLoop,
        window: Mock,
        terminal: Terminal,
    ) -> None:
        async def read() -> int:
            window_input = WindowInput(window, input_fd=terminal.input_fd)
            assert window_input.window is window
            return await window_input.getch()

        terminal.queued.append(ord("x"))
        assert loop.run_until_complete(read()) == ord("x")

    def test_waits_for_key(
        self,
        loop: asyncio.AbstractEventLoop,
        window: Mock,
        terminal: Terminal,
    ) -> None:
        async def read() -> int:
            window_input = WindowInput(window, input_fd=terminal.input_fd)
            return await window_input.getch()

        loop.call_later(0.01, terminal.type, b"y")
        assert loop.run_until_complete(asyncio.wait_for(read(), 5)) == ord(
            "y"
        )

    def test_wake(
        self,
        loop: asyncio.AbstractEventLoop,
        window: Mock,
        terminal: Terminal,
    ) -> None:
        async def read_after_wake() -> int:
            window_input = WindowInput(window, input_fd=terminal.input_fd)
            task = loop.create_task(window_input.getch())
            await asyncio.sleep(0.01)
            # A key pushed back from outside the loop shows on no descriptor.
            terminal.queued.append(ord("w"))
            window_input.waiter.wake()
            return await asyncio.wait_for(task, 5)

        assert loop.run_until_complete(read_after_wake()) == ord("w")

    def test_rejects_other_loop(self, window: Mock) -> None:
        async def create() -> None:
            WindowInput(window)

        with contextlib.closing(asyncio.SelectorEventLoop()) as loop:
            with pytest.raises(TypeError, match="EventLoop"):
                loop.run_until_complete(create())


@needs_unix
class TestEventLoop:
    @pytest.fixture(autouse=True, params=["runner", "legacy"])
    def fixture_runner(
        self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if request.param == "legacy":
            monkeypatch.delattr(asyncio, "Runner", raising=False)

    @pytest.fixture(autouse=True)
    def fixture_initialised(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(curses, "isendwin", Mock(return_value=False))

    def test_reads_stdin(self, window: Mock, stdin: Terminal) -> None:
        async def app() -> int:
            stdin.type(b"r")
            return await WindowInput(window).getch()

        assert asyncio_ext.run(app(), loop_factory=EventLoop) == ord("r")

    @needs_sigwinch
    def test_resize(
        self,
        window: Mock,
        stdin: Terminal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sizes = []  # type: List[List[int]]

        def resizeterm(lines: int, columns: int) -> None:
            sizes.append([lines, columns])
            curses.ungetch(curses.KEY_RESIZE)

        monkeypatch.setattr(
            os, "get_terminal_size", lambda: os.terminal_size((100, 30))
        )
        monkeypatch.setattr(curses, "resizeterm", resizeterm)

        async def app() -> int:
            os.kill(os.getpid(), signal.SIGWINCH)
            return await asyncio.wait_for(WindowInput(window).getch(), 5)

        del stdin
        assert asyncio_ext.run(app(), loop_factory=EventLoop) == (
            curses.KEY_RESIZE
        )
        assert sizes == [[30, 100]]

    def test_without_sigwinch(
        self,
        window: Mock,
        stdin: Terminal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delattr(signal, "SIGWINCH", raising=False)

        async def app() -> int:
            stdin.type(b"s")
            return await WindowInput(window).getch()

        assert asyncio_ext.run(app(), loop_factory=EventLoop) == ord("s")


class TestInitialise:
    def test_nodelay_while_entered(self, window: Mock) -> None:
        with initialise() as given:
            assert given is window
            assert window.nodelay.call_args_list == [((True,),)]
        window.nodelay.assert_called_with(False)
        curses.endwin.assert_called_once()  # type: ignore[attr-defined]

    def test_initscr(self, window: Mock) -> None:
        other = Mock()
        with initialise(initscr=lambda: other) as given:
            assert given is other
        window.nodelay.assert_not_called()

    @needs_sigwinch
    def test_keeps_resize_handler(self, window: Mock) -> None:
        del window
        previous = signal.getsignal(signal.SIGWINCH)
        with initialise():
            # A Python handler, so ncurses does not install its own.
            assert callable(signal.getsignal(signal.SIGWINCH))
        assert signal.getsignal(signal.SIGWINCH) == previous

    def test_terminal_cleanup_on_failure(self, window: Mock) -> None:
        with pytest.raises(ValueError, match="application failed"):
            with initialise():
                raise ValueError("application failed")
        window.keypad.assert_called_with(False)
        window.nodelay.assert_called_with(False)
        curses.endwin.assert_called_once()  # type: ignore[attr-defined]


class TestResize:
    def test_resizes_to_terminal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            os, "get_terminal_size", lambda: os.terminal_size((100, 30))
        )
        resizeterm = Mock()
        monkeypatch.setattr(curses, "resizeterm", resizeterm)
        _resize()
        resizeterm.assert_called_once_with(30, 100)

    def test_without_terminal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def no_terminal() -> os.terminal_size:
            raise OSError("not a terminal")

        monkeypatch.setattr(os, "get_terminal_size", no_terminal)
        resizeterm = Mock()
        monkeypatch.setattr(curses, "resizeterm", resizeterm)
        _resize()
        resizeterm.assert_not_called()


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
