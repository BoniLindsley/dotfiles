#!/usr/bin/env python3
"""An asyncio selector loop that reads ncurses input without polling.

The loop waits in its selector, never inside curses: terminal input is
one more readable file descriptor, and keys are read with nodelay
``getch`` when it is ready. Thread-safe callbacks use asyncio's own
wakeup, and socket, pipe and subprocess readiness work as usual.
"""

# Shares code with asyncio_loop, the loop this one is meant to replace.
# pylint: disable=duplicate-code

# Standard libraries.
import asyncio
import collections
import contextlib
import curses
import selectors
import typing

from typing import Iterator, List, Mapping, Tuple, Union

# Internal modules.
from .. import asyncio_ext
from . import raii

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


class EventLoop(asyncio.SelectorEventLoop):
    """Run asyncio with ncurses input on ``input_fd``, standard input.

    Run on the main thread and keep curses calls there.
    Owns ``window``'s input: it is set to nodelay mode,
    and keys are read only through ``getch()``.
    Closing restores blocking input.
    Applications control screen updates with refresh(),
    or noutrefresh() followed by curses.doupdate().
    Submit worker-thread callbacks with call_soon_threadsafe().
    """

    def __init__(self, *, stdscr: "curses.window", input_fd: int = 0) -> None:
        self.window = stdscr
        self._input_fd = input_fd
        self._input_waiters = (
            collections.deque()
        )  # type: typing.Deque[asyncio.Future[int]]
        self._keys = collections.deque()  # type: typing.Deque[int]
        super().__init__(_Selector(selectors.DefaultSelector(), self))
        stdscr.nodelay(True)
        self.add_reader(input_fd, self._read_keys)

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
            self.remove_reader(self._input_fd)
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

    Restores the terminal and previous policy even on exceptions.
    Unfinished tasks are cancelled and awaited.
    """
    with raii.initialise() as window:
        with use_event_loop_policy(window):
            return asyncio_ext.run(coro)
