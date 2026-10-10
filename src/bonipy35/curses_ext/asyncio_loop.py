#!/usr/bin/env python3
"""An asyncio loop that waits in ncurses, without periodic polling."""

# Standard libraries.
import asyncio
import collections
import contextlib
import curses
import math
import selectors
import signal
import threading
import typing

from typing import Iterator, List, Tuple, Union

# Internal modules.
from .. import asyncio_ext
from . import raii

_T = typing.TypeVar("_T")


class _Selector:
    """Adapt asyncio's next deadline to ncurses' blocking input wait."""

    def __init__(self, loop: "EventLoop") -> None:
        self._loop = loop

    def select(
        self, timeout: Union[None, float] = None
    ) -> List[Tuple[selectors.SelectorKey, int]]:
        milliseconds = (
            -1
            if timeout is None
            else min(2147483647, max(0, math.ceil(timeout * 1000)))
        )
        self._loop.window.timeout(milliseconds)
        key = self._loop.window.getch()
        if key in (-1, self._loop.wakeup_key):
            return []
        # Ncurses consumes stdin itself; attach its decoded key as event data.
        input_key = selectors.SelectorKey(
            fileobj=0, fd=0, events=selectors.EVENT_READ, data=key
        )
        return [(input_key, selectors.EVENT_READ)]


# Unsupported transport factories deliberately retain NotImplementedError.
class EventLoop(asyncio.BaseEventLoop):  # pylint: disable=abstract-method
    """Run asyncio tasks and timers using ncurses as the wait mechanism.

    Run on the main thread of a Unix process and keep curses calls there.
    Tasks, futures, timers, executors and thread-safe callbacks are supported;
    socket, pipe, subprocess and file-descriptor readiness are unsupported.

    Owns input and timeout settings on ``window``; do not read it elsewhere.
    Closing restores blocking input. Applications control screen updates with
    refresh(), or noutrefresh() followed by curses.doupdate(). Ncurses may
    refresh a modified input window during reads; draw to separate windows
    for precise batching. Recalculate layouts after KEY_RESIZE. Escape-key
    decoding may introduce a delay controlled by ncurses.

    Submit worker-thread callbacks with call_soon_threadsafe(). Override
    ``wakeup_key`` and ``wakeup_signal`` before running if needed. The key is
    reserved for internal use; applications must not use the signal
    concurrently. The signal defaults to SIGUSR1, and its previous handler is
    restored after each run.
    """

    wakeup_key = curses.KEY_MAX + 1
    wakeup_signal = signal.SIGUSR1

    def __init__(self, *, stdscr: "curses.window") -> None:
        super().__init__()
        self.window = stdscr
        self._input_waiters = (
            collections.deque()
        )  # type: typing.Deque[asyncio.Future[int]]
        self._keys = collections.deque()  # type: typing.Deque[int]
        self._selector = _Selector(self)
        self._signal_installed = False
        self._wakeup_lock = threading.Lock()

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

    def _process_events(
        self, event_list: List[Tuple[selectors.SelectorKey, int]]
    ) -> None:
        for selector_key, _event_mask in event_list:
            del _event_mask
            key = typing.cast(int, selector_key.data)
            while self._input_waiters and self._input_waiters[0].done():
                self._input_waiters.popleft()
            if self._input_waiters:
                self._input_waiters.popleft().set_result(key)
            else:
                self._keys.append(key)

    def _wake(self, signum: int, frame: typing.Any) -> None:
        del signum, frame
        try:
            # Python executes this handler on the main thread, after the
            # interrupted curses call returns. Queueing a key also covers
            # a signal delivered just before entering the blocking wait.
            curses.ungetch(self.wakeup_key)
        except curses.error:
            # A full ncurses pushback queue already makes getch ready.
            pass

    def _write_to_self(self) -> None:
        with self._wakeup_lock:
            if self._signal_installed and self.is_running():
                thread_id = threading.main_thread().ident
                assert thread_id is not None
                # Target the waiting thread; process signals can instead be
                # delivered to an unrelated worker and leave getch blocked.
                signal.pthread_kill(thread_id, self.wakeup_signal)

    def run_forever(self) -> None:
        wakeup_signal = self.wakeup_signal
        previous = signal.signal(wakeup_signal, self._wake)
        self._signal_installed = True
        try:
            super().run_forever()
        finally:
            with self._wakeup_lock:
                self._signal_installed = False
                signal.signal(wakeup_signal, previous)

    def close(self) -> None:
        if self.is_running():
            raise RuntimeError("Cannot close a running event loop")
        if self.is_closed():
            return
        while self._input_waiters:
            self._input_waiters.popleft().cancel()
        self._keys.clear()
        try:
            self.window.timeout(-1)
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
    """Temporarily install a curses policy.

    Restore the previous policy on exit.
    Use when the caller already owns curses initialization.
    Callers must cancel tasks and close loops they create.
    This context does not manage their lifetime.
    """
    previous = asyncio.get_event_loop_policy()
    policy = EventLoopPolicy(stdscr=stdscr)
    asyncio.set_event_loop_policy(policy)
    try:
        yield policy
    finally:
        asyncio.set_event_loop_policy(previous)


def run(coro: "typing.Coroutine[typing.Any, typing.Any, _T]") -> _T:
    """Run a coroutine with curses initialized and its event-loop policy set.

    The called coroutine
    can retrieve its loop using `asyncio.get_event_loop()`.
    Call from the main thread, outside an existing running event loop.
    Restore the terminal and previous policy even on exceptions.
    Return normally to quit;
    Ctrl+C raises KeyboardInterrupt after cleanup.
    Unfinished tasks are cancelled and awaited,
    so they must allow cancellation to complete.
    """
    with raii.initialise() as window:
        with use_event_loop_policy(window):
            return asyncio_ext.run(coro)
