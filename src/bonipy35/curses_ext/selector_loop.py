#!/usr/bin/env python3
"""An asyncio selector loop that reads ncurses input without polling.

The loop waits in its selector, never inside curses: terminal input is
one more readable file descriptor, and keys are read with nodelay
``getch`` when it is ready. Thread-safe callbacks use asyncio's own
wakeup, and socket, pipe and subprocess readiness work as usual.

On Windows, the wait covers the console input and the loop's sockets,
which are the only readiness Windows selectors support.
"""

# Standard libraries.
import asyncio
import collections
import contextlib
import curses
import selectors
import signal
import sys
import typing

from typing import Iterator, List, Mapping, Tuple, Union

# Internal modules.
from .. import asyncio_ext
from . import raii
from .input_loop import _resize, keep_resize_handler

_T = typing.TypeVar("_T")


class _Selector(selectors.BaseSelector):
    """Read keys already queued inside curses before each wait.

    Curses queues keys that its input file descriptor no longer shows,
    such as pushed back keys, so waiting on that alone could miss them.
    """

    def __init__(
        self, selector: selectors.BaseSelector, loop: "EventLoop"
    ) -> None:
        self._selector = selector
        self._loop = loop

    def register(
        self, fileobj: typing.Any, events: int, data: typing.Any = None
    ) -> selectors.SelectorKey:
        return self._selector.register(fileobj, events, data)

    def unregister(self, fileobj: typing.Any) -> selectors.SelectorKey:
        return self._selector.unregister(fileobj)

    def modify(
        self, fileobj: typing.Any, events: int, data: typing.Any = None
    ) -> selectors.SelectorKey:
        return self._selector.modify(fileobj, events, data)

    def select(
        self, timeout: Union[None, float] = None
    ) -> List[Tuple[selectors.SelectorKey, int]]:
        # pylint: disable-next=protected-access
        if self._loop._read_keys():
            # Keys were handed to waiters; collect other events only.
            timeout = 0
        return self._selector.select(timeout)

    def close(self) -> None:
        self._selector.close()

    def get_map(self) -> Mapping[typing.Any, selectors.SelectorKey]:
        return self._selector.get_map()


class _ConsoleSelector(_Selector):
    """Wait on a Windows console and the registered sockets together.

    Registered sockets are bound to an event of ``console``,
    which also waits on the console input.
    Sockets bound this way signal only new network events,
    so readiness is checked before waiting as well as after.
    """

    def __init__(
        self,
        selector: selectors.BaseSelector,
        loop: "EventLoop",
        console: typing.Any,
    ) -> None:
        super().__init__(selector, loop)
        self._console = console

    def register(
        self, fileobj: typing.Any, events: int, data: typing.Any = None
    ) -> selectors.SelectorKey:
        key = super().register(fileobj, events, data)
        try:
            self._console.bind(key.fd, events)
        except BaseException:
            super().unregister(fileobj)
            raise
        return key

    def unregister(self, fileobj: typing.Any) -> selectors.SelectorKey:
        key = super().unregister(fileobj)
        self._console.unbind(key.fd)
        return key

    def modify(
        self, fileobj: typing.Any, events: int, data: typing.Any = None
    ) -> selectors.SelectorKey:
        key = super().modify(fileobj, events, data)
        self._console.bind(key.fd, events)
        return key

    def select(
        self, timeout: Union[None, float] = None
    ) -> List[Tuple[selectors.SelectorKey, int]]:
        # pylint: disable-next=protected-access
        found = self._loop._read_keys()
        # Network events after this check signal the event again.
        self._console.reset()
        ready = self._selector.select(0)
        if found or ready or (timeout is not None and timeout <= 0):
            return ready
        self._console.wait(timeout)
        self._loop._read_keys()  # pylint: disable=protected-access
        return self._selector.select(0)

    def close(self) -> None:
        try:
            super().close()
        finally:
            self._console.close()


if sys.platform == "win32":  # pragma: no cover
    # Internal modules, Windows-only.
    from .input_loop import _Console


def _new_console() -> typing.Any:
    """Return the Windows console to wait on, or None to use descriptors."""
    if sys.platform == "win32":  # pragma: no cover
        return _Console()
    return None


class EventLoop(asyncio.SelectorEventLoop):
    """Run asyncio with ncurses input on ``input_fd``, standard input.

    Run on the main thread and keep curses calls there.
    Owns ``window``'s input: it is set to nodelay mode,
    and keys are read only through ``getch()``.
    Closing restores blocking input.
    Applications control screen updates with refresh(),
    or noutrefresh() followed by curses.doupdate().
    Submit worker-thread callbacks with call_soon_threadsafe().

    Where SIGWINCH exists, the loop handles it by resizing curses
    to the terminal, which queues `KEY_RESIZE` for ``getch()``.
    Ncurses installs its own handler at initialisation
    only if none is set, and never again,
    so install a Python handler before initialising curses
    and restore it after ending curses, as ``run()`` does.

    On Windows, input comes from the console and ``input_fd`` is unused.
    `KEY_RESIZE` resizes curses to the console before ``getch()`` returns it,
    and the loop takes over the signal wakeup file descriptor,
    as asyncio's own Windows loop does, so that Ctrl+C ends a wait.
    """

    def __init__(self, *, stdscr: "curses.window", input_fd: int = 0) -> None:
        self.window = stdscr
        self._input_fd = input_fd
        self._input_waiters = (
            collections.deque()
        )  # type: typing.Deque[asyncio.Future[int]]
        self._keys = collections.deque()  # type: typing.Deque[int]
        self._console = _new_console()
        if self._console is None:
            selector = _Selector(selectors.DefaultSelector(), self)
        else:
            selector = _ConsoleSelector(
                selectors.DefaultSelector(), self, self._console
            )
        super().__init__(selector)
        stdscr.nodelay(True)
        if self._console is None:
            self.add_reader(input_fd, self._read_keys)
            if hasattr(signal, "SIGWINCH"):
                self.add_signal_handler(signal.SIGWINCH, _resize)
        else:
            self._previous_wakeup_fd = signal.set_wakeup_fd(
                self._csock.fileno()  # type: ignore[attr-defined]
            )

    def create_future(self) -> "asyncio.Future[typing.Any]":
        # BaseEventLoop.create_future was added in Python 3.5.2.
        return asyncio.Future(loop=self)

    async def getch(self) -> int:
        """Return the next integer key code.

        Concurrent requests are FIFO.
        Cancellation removes only this request.
        Keys read while no request is waiting are buffered,
        including `KEY_RESIZE` and `KEY_MOUSE`.
        """
        if self.is_closed():
            raise RuntimeError("Event loop is closed")
        if asyncio.get_event_loop() is not self:
            raise RuntimeError("getch must run on its owning event loop")
        if self._keys:
            return self._keys.popleft()
        future = self.create_future()  # type: asyncio.Future[int]
        self._input_waiters.append(future)
        try:
            return await future
        finally:
            try:
                self._input_waiters.remove(future)
            except ValueError:
                pass

    def _read_keys(self) -> bool:
        """Hand every key curses has to waiters; return whether any."""
        found = False
        while True:
            key = self.window.getch()
            if key == -1:
                return found
            found = True
            if key == curses.KEY_RESIZE and self._console is not None:
                # PDCurses resizes only when asked to.
                curses.resize_term(0, 0)
            while self._input_waiters and self._input_waiters[0].done():
                self._input_waiters.popleft()
            if self._input_waiters:
                self._input_waiters.popleft().set_result(key)
            else:
                self._keys.append(key)

    def close(self) -> None:
        if self.is_running():
            raise RuntimeError("Cannot close a running event loop")
        if self.is_closed():
            return
        while self._input_waiters:
            self._input_waiters.popleft().cancel()
        self._keys.clear()
        try:
            if self._console is None:
                self.remove_reader(self._input_fd)
            else:
                signal.set_wakeup_fd(self._previous_wakeup_fd)
            self.window.nodelay(False)
        finally:
            super().close()


class EventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def __init__(self, *, stdscr: "curses.window") -> None:
        super().__init__()
        self._stdscr = stdscr

    def new_event_loop(self) -> EventLoop:
        return EventLoop(stdscr=self._stdscr)


@contextlib.contextmanager
def use_event_loop_policy(
    stdscr: "curses.window",
) -> Iterator[EventLoopPolicy]:
    """Temporarily install a curses policy, restoring the previous one.

    Callers must cancel tasks and close loops they create.
    """
    previous = asyncio.get_event_loop_policy()
    policy = EventLoopPolicy(stdscr=stdscr)
    asyncio.set_event_loop_policy(policy)
    try:
        yield policy
    finally:
        asyncio.set_event_loop_policy(previous)


def run(coro: "typing.Coroutine[typing.Any, typing.Any, _T]") -> _T:
    """Run a coroutine with curses initialised and this loop's policy set.

    Restores the terminal, SIGWINCH handler and previous policy
    even on exceptions.
    Unfinished tasks are cancelled and awaited.
    """
    with keep_resize_handler():
        with raii.initialise() as window:
            with use_event_loop_policy(window):
                return asyncio_ext.run(coro)
