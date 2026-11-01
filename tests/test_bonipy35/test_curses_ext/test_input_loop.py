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
import select
import selectors
import signal
import socket
import sys
import threading
import time
import typing

from typing import Dict, Iterator, List, Optional, Tuple
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35 import asyncio_ext
from bonipy35.curses_ext.input_loop import (
    ConsoleSelector,
    EventLoop,
    InputSelector,
    InputWaiter,
    WindowInput,
    _resize,
    initialise,
    keep_resize_handler,
    run,
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
) -> Iterator[EventLoop]:
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


class FakeConsole:
    """Stand in for the Windows console, waiting with ``select``.

    The terminal's input socket plays the console input handle;
    bound descriptors play sockets bound to the console's event.
    """

    def __init__(self, terminal: Terminal) -> None:
        self.input_fd = terminal.input_fd
        self.bound = {}  # type: Dict[int, int]
        self.resets = 0
        self.waits = []  # type: List[Tuple[Optional[float], bool]]
        self.closes = 0

    def bind(self, fd: int, events: int) -> None:
        self.bound[fd] = events

    def unbind(self, fd: int) -> None:
        del self.bound[fd]

    def reset(self) -> None:
        self.resets += 1

    def wait(self, timeout: Optional[float], with_input: bool) -> None:
        self.waits.append((timeout, with_input))
        readers = [
            fd
            for fd, events in self.bound.items()
            if events & selectors.EVENT_READ
        ]
        if with_input:
            readers.append(self.input_fd)
        writers = [
            fd
            for fd, events in self.bound.items()
            if events & selectors.EVENT_WRITE
        ]
        select.select(readers, writers, [], timeout)

    def close(self) -> None:
        self.closes += 1


@pytest.fixture(name="console")
def fixture_console(terminal: Terminal) -> FakeConsole:
    return FakeConsole(terminal)


@pytest.fixture(name="console_selector")
def fixture_console_selector(
    window: Mock, terminal: Terminal, console: FakeConsole
) -> Iterator[ConsoleSelector]:
    with ConsoleSelector(
        window=window, input_fd=terminal.input_fd, console=console
    ) as selector:
        yield selector


def is_registered(
    selector: selectors.BaseSelector, terminal: Terminal
) -> bool:
    return terminal.input_fd in selector.get_map()


def inner_map(
    selector: ConsoleSelector,
) -> typing.Mapping[typing.Any, selectors.SelectorKey]:
    """Return the keys of the selector that the console mixin is over."""
    return selectors.SelectSelector.get_map(selector)


class TestInputSelectorMixin:
    def test_input_fd(
        self, selector: InputSelector, terminal: Terminal
    ) -> None:
        assert selector.input_fd == terminal.input_fd

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


class TestConsoleSelectorMixin:
    def test_input_kept_out_of_selector(
        self,
        console_selector: ConsoleSelector,
        console: FakeConsole,
        terminal: Terminal,
    ) -> None:
        key = console_selector.register(
            terminal.input_fd, selectors.EVENT_READ, "data"
        )
        assert key == selectors.SelectorKey(
            terminal.input_fd, terminal.input_fd, selectors.EVENT_READ, "data"
        )
        assert terminal.input_fd not in inner_map(console_selector)
        assert not console.bound
        assert console_selector.get_key(terminal.input_fd) is key
        assert console_selector.get_key(terminal.input_socket) is key
        assert dict(console_selector.get_map()) == {terminal.input_fd: key}
        assert console_selector.unregister(terminal.input_fd) is key
        assert not console_selector.get_map()

    def test_input_and_sockets_mapped(
        self, console_selector: ConsoleSelector, terminal: Terminal
    ) -> None:
        reader, writer = socket.socketpair()
        with reader, writer:
            other = console_selector.register(reader, selectors.EVENT_READ)
            key = console_selector.register(
                terminal.input_fd, selectors.EVENT_READ
            )
            assert dict(console_selector.get_map()) == {
                reader.fileno(): other,
                terminal.input_fd: key,
            }
            assert console_selector.get_key(reader) is other
            assert len(console_selector.get_map()) == 2

    @pytest.mark.parametrize(
        "events",
        [selectors.EVENT_WRITE, selectors.EVENT_READ | selectors.EVENT_WRITE],
    )
    def test_input_read_only(
        self,
        console_selector: ConsoleSelector,
        terminal: Terminal,
        events: int,
    ) -> None:
        with pytest.raises(ValueError):
            console_selector.register(terminal.input_fd, events)
        key = console_selector.register(
            terminal.input_fd, selectors.EVENT_READ
        )
        with pytest.raises(ValueError):
            console_selector.modify(terminal.input_fd, events)
        assert console_selector.get_key(terminal.input_fd) is key

    def test_input_registered_once(
        self, console_selector: ConsoleSelector, terminal: Terminal
    ) -> None:
        with pytest.raises(KeyError):
            console_selector.unregister(terminal.input_fd)
        with pytest.raises(KeyError):
            console_selector.modify(terminal.input_fd, selectors.EVENT_READ)
        console_selector.register(terminal.input_fd, selectors.EVENT_READ)
        with pytest.raises(KeyError):
            console_selector.register(terminal.input_fd, selectors.EVENT_READ)

    def test_modify_input_data(
        self, console_selector: ConsoleSelector, terminal: Terminal
    ) -> None:
        console_selector.register(terminal.input_fd, selectors.EVENT_READ, 1)
        key = console_selector.modify(
            terminal.input_fd, selectors.EVENT_READ, 2
        )
        assert key.data == 2
        assert console_selector.get_key(terminal.input_fd) is key

    def test_sockets_bound(
        self, console_selector: ConsoleSelector, console: FakeConsole
    ) -> None:
        reader, writer = socket.socketpair()
        with reader, writer:
            fd = reader.fileno()
            console_selector.register(fd, selectors.EVENT_READ)
            assert console.bound == {fd: selectors.EVENT_READ}
            assert fd in inner_map(console_selector)
            console_selector.modify(fd, selectors.EVENT_WRITE)
            assert console.bound == {fd: selectors.EVENT_WRITE}
            console_selector.unregister(fd)
            assert not console.bound
            assert fd not in inner_map(console_selector)

    def test_bind_failure(
        self,
        console_selector: ConsoleSelector,
        console: FakeConsole,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(console, "bind", Mock(side_effect=OSError))
        reader, writer = socket.socketpair()
        with reader, writer:
            with pytest.raises(OSError):
                console_selector.register(reader, selectors.EVENT_READ)
            assert reader.fileno() not in console_selector.get_map()

    def test_invalid_file_object(
        self, console_selector: ConsoleSelector
    ) -> None:
        with pytest.raises(ValueError):
            console_selector.register(object(), selectors.EVENT_READ)

    def test_queued_key(
        self,
        console_selector: ConsoleSelector,
        console: FakeConsole,
        terminal: Terminal,
    ) -> None:
        key = console_selector.register(
            terminal.input_fd, selectors.EVENT_READ
        )
        terminal.queued.append(ord("a"))
        assert console_selector.select(None) == [(key, selectors.EVENT_READ)]
        assert not console.waits

    def test_other_ready_kept(
        self, console_selector: ConsoleSelector, terminal: Terminal
    ) -> None:
        reader, writer = socket.socketpair()
        with reader, writer:
            other = console_selector.register(reader, selectors.EVENT_READ)
            key = console_selector.register(
                terminal.input_fd, selectors.EVENT_READ
            )
            writer.sendall(b"x")
            terminal.queued.append(ord("a"))
            assert console_selector.select(None) == [
                (other, selectors.EVENT_READ),
                (key, selectors.EVENT_READ),
            ]

    def test_ready_socket_without_wait(
        self, console_selector: ConsoleSelector, console: FakeConsole
    ) -> None:
        reader, writer = socket.socketpair()
        with reader, writer:
            other = console_selector.register(reader, selectors.EVENT_READ)
            writer.sendall(b"x")
            assert console_selector.select(None) == [
                (other, selectors.EVENT_READ)
            ]
            assert not console.waits

    def test_wakes_for_typed_key(
        self,
        console_selector: ConsoleSelector,
        console: FakeConsole,
        terminal: Terminal,
    ) -> None:
        key = console_selector.register(
            terminal.input_fd, selectors.EVENT_READ
        )
        timer = threading.Timer(0.02, terminal.type, [b"a"])
        timer.start()
        try:
            assert console_selector.select(None) == [
                (key, selectors.EVENT_READ)
            ]
        finally:
            timer.join()
        assert console.waits == [(None, True)]
        assert list(terminal.queued) == [ord("a")]

    def test_wakes_for_socket(
        self, console_selector: ConsoleSelector, terminal: Terminal
    ) -> None:
        console_selector.register(terminal.input_fd, selectors.EVENT_READ)
        reader, writer = socket.socketpair()
        with reader, writer:
            other = console_selector.register(reader, selectors.EVENT_READ)
            timer = threading.Timer(0.02, writer.sendall, [b"x"])
            timer.start()
            try:
                assert console_selector.select(None) == [
                    (other, selectors.EVENT_READ)
                ]
            finally:
                timer.join()

    def test_console_input_only_while_registered(
        self,
        console_selector: ConsoleSelector,
        console: FakeConsole,
        terminal: Terminal,
    ) -> None:
        terminal.type(b"a")
        assert not console_selector.select(0.01)
        assert [with_input for _, with_input in console.waits] == [False]
        assert terminal.reads == 0

    def test_zero_timeout(
        self,
        console_selector: ConsoleSelector,
        console: FakeConsole,
        terminal: Terminal,
    ) -> None:
        console_selector.register(terminal.input_fd, selectors.EVENT_READ)
        assert not console_selector.select(0)
        assert not console.waits
        assert console.resets == 1

    def test_other_console_events_keep_timeout(
        self,
        console_selector: ConsoleSelector,
        console: FakeConsole,
        terminal: Terminal,
        window: Mock,
    ) -> None:
        def getch() -> int:
            # Curses drains console events that are not keys,
            # such as focus changes and key releases.
            terminal.reads += 1
            try:
                terminal.input_socket.recv(1)
            except BlockingIOError:
                pass
            return -1

        window.getch.side_effect = getch
        console_selector.register(terminal.input_fd, selectors.EVENT_READ)
        # One event for the peek before waiting, one to wake the wait.
        terminal.type(b"\0\0")
        start = time.monotonic()
        assert not console_selector.select(0.1)
        assert time.monotonic() - start >= 0.09
        timeouts = [timeout for timeout, _ in console.waits]
        assert len(timeouts) == 2
        assert typing.cast(float, timeouts[1]) < typing.cast(
            float, timeouts[0]
        )
        assert terminal.reads == 3

    def test_close(
        self,
        console_selector: ConsoleSelector,
        console: FakeConsole,
        terminal: Terminal,
    ) -> None:
        console_selector.register(terminal.input_fd, selectors.EVENT_READ)
        console_selector.close()
        assert console.closes == 1
        with pytest.raises(RuntimeError, match="closed"):
            console_selector.get_key(terminal.input_fd)

    @pytest.mark.skipif(sys.platform == "win32", reason="has a console")
    def test_default_console_needs_windows(self, window: Mock) -> None:
        with pytest.raises(RuntimeError, match="Windows"):
            ConsoleSelector(window=window)

    def test_waiter_on_stock_loop(
        self,
        console_selector: ConsoleSelector,
        terminal: Terminal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Real windows-curses resizes inside getch before returning
        # KEY_RESIZE, and every resize_term flushes console input.
        monkeypatch.setattr(curses, "resize_term", Mock())
        loop = asyncio.SelectorEventLoop(console_selector)
        with contextlib.closing(loop):
            waiter = InputWaiter(loop, input_fd=terminal.input_fd)
            loop.call_later(0.01, terminal.ungetch, curses.KEY_RESIZE)
            loop.run_until_complete(asyncio.wait_for(waiter.input_ready(), 5))
            assert not is_registered(console_selector, terminal)
        assert list(terminal.queued) == [curses.KEY_RESIZE]
        curses.resize_term.assert_not_called()  # type: ignore[attr-defined]


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
            window_input = WindowInput(window)
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
            window_input = WindowInput(window)
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
            window_input = WindowInput(window)
            task = loop.create_task(window_input.getch())
            await asyncio.sleep(0.01)
            # A key pushed back from outside the loop shows on no descriptor.
            terminal.queued.append(ord("w"))
            window_input.waiter.wake()
            return await asyncio.wait_for(task, 5)

        assert loop.run_until_complete(read_after_wake()) == ord("w")

    def test_any_loop_with_input_selector(
        self, selector: InputSelector, window: Mock, terminal: Terminal
    ) -> None:
        class OtherLoop(asyncio.SelectorEventLoop):
            @property
            def input_selector(self) -> InputSelector:
                return selector

        async def read() -> int:
            return await WindowInput(window).getch()

        with contextlib.closing(OtherLoop(selector)) as loop:
            loop.call_later(0.01, terminal.type, b"o")
            assert loop.run_until_complete(
                asyncio.wait_for(read(), 5)
            ) == ord("o")

    def test_rejects_loop_without_input_selector(self, window: Mock) -> None:
        async def create() -> None:
            WindowInput(window)

        with contextlib.closing(asyncio.SelectorEventLoop()) as loop:
            with pytest.raises(TypeError, match="input_selector"):
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

    def test_input_selector(
        self, loop: EventLoop, selector: InputSelector
    ) -> None:
        assert loop.input_selector is selector

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


class TestRun:
    def test_reads_stdin(self, window: Mock, stdin: Terminal) -> None:
        async def app(given: "curses.window") -> int:
            assert given is window
            assert asyncio.get_event_loop().is_running()
            stdin.type(b"r")
            return await WindowInput(given).getch()

        assert run(app) == ord("r")
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
