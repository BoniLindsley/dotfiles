#!/usr/bin/env python3
"""An asyncio selector loop that reads ncurses input without polling.

The loop waits in its selector, never inside curses: terminal input is
one more readable file descriptor, and keys are read with nodelay
``getch`` when it is ready. Thread-safe callbacks use asyncio's own
wakeup, and socket, pipe and subprocess readiness work as usual.

On Windows, the wait covers the console input and the loop's sockets,
which are the only readiness Windows selectors support.

Run ``python -m bonipy35.curses_ext.selector_loop`` to check a terminal.
"""

# Standard libraries.
import asyncio
import collections
import contextlib
import curses
import math
import os
import selectors
import signal
import sys
import threading
import time
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
    # Standard libraries, Windows-only.
    import ctypes

    from ctypes import wintypes

    _FD_READ = 0x01
    _FD_WRITE = 0x02
    _FD_ACCEPT = 0x08
    _FD_CONNECT = 0x10
    _FD_CLOSE = 0x20
    _STD_INPUT_HANDLE = -10 & 0xFFFFFFFF
    _INFINITE = 0xFFFFFFFF
    _WAIT_FAILED = 0xFFFFFFFF
    # A function, its result type and its argument types.
    _Signature = typing.Tuple[typing.Any, typing.Any, typing.List[typing.Any]]

    class _Console:
        """Wait on the console input and an event bound to sockets.

        ``console_input`` is a handle to wait on for input,
        by default standard input's.
        """

        def __init__(self, console_input: Union[None, int] = None) -> None:
            self._kernel32 = kernel32 = ctypes.WinDLL(
                "kernel32", use_last_error=True
            )
            self._ws2_32 = ws2_32 = ctypes.WinDLL(
                "ws2_32", use_last_error=True
            )
            signatures = (
                (kernel32.GetStdHandle, wintypes.HANDLE, [wintypes.DWORD]),
                (
                    kernel32.CreateEventW,
                    wintypes.HANDLE,
                    [
                        wintypes.LPVOID,
                        wintypes.BOOL,
                        wintypes.BOOL,
                        wintypes.LPCWSTR,
                    ],
                ),
                (kernel32.ResetEvent, wintypes.BOOL, [wintypes.HANDLE]),
                (kernel32.CloseHandle, wintypes.BOOL, [wintypes.HANDLE]),
                (
                    kernel32.WaitForMultipleObjects,
                    wintypes.DWORD,
                    [
                        wintypes.DWORD,
                        ctypes.POINTER(wintypes.HANDLE),
                        wintypes.BOOL,
                        wintypes.DWORD,
                    ],
                ),
                (
                    ws2_32.WSAEventSelect,
                    ctypes.c_int,
                    [wintypes.WPARAM, wintypes.HANDLE, ctypes.c_long],
                ),
            )  # type: typing.Sequence[_Signature]
            for function, restype, argtypes in signatures:
                function.restype = restype
                function.argtypes = argtypes
            if console_input is None:
                console_input = kernel32.GetStdHandle(_STD_INPUT_HANDLE)
            self._event = kernel32.CreateEventW(None, True, False, None)
            if not self._event:
                raise ctypes.WinError(ctypes.get_last_error())
            self._handles = (wintypes.HANDLE * 2)(console_input, self._event)

        def bind(self, fd: int, events: int) -> None:
            flags = 0
            if events & selectors.EVENT_READ:
                flags |= _FD_READ | _FD_ACCEPT | _FD_CLOSE
            if events & selectors.EVENT_WRITE:
                flags |= _FD_WRITE | _FD_CONNECT | _FD_CLOSE
            if self._ws2_32.WSAEventSelect(fd, self._event, flags):
                raise ctypes.WinError(ctypes.get_last_error())

        def unbind(self, fd: int) -> None:
            # Fails harmlessly for a socket closed before unregistering.
            self._ws2_32.WSAEventSelect(fd, None, 0)

        def reset(self) -> None:
            self._kernel32.ResetEvent(self._event)

        def wait(self, timeout: Union[None, float]) -> None:
            milliseconds = (
                _INFINITE
                if timeout is None
                else min(_INFINITE - 1, max(0, math.ceil(timeout * 1000)))
            )
            if (
                self._kernel32.WaitForMultipleObjects(
                    2, self._handles, False, milliseconds
                )
                == _WAIT_FAILED
            ):
                raise ctypes.WinError(ctypes.get_last_error())

        def close(self) -> None:
            self._kernel32.CloseHandle(self._event)


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
                self.add_signal_handler(signal.SIGWINCH, self._resize)
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

    def _resize(self) -> None:
        try:
            columns, lines = os.get_terminal_size()
        except OSError:
            return
        # Queues KEY_RESIZE if the size changed.
        curses.resizeterm(lines, columns)

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


def _ignore_signal(signum: int, frame: typing.Any) -> None:
    del signum, frame


@contextlib.contextmanager
def keep_resize_handler() -> Iterator[None]:
    """Hold a Python SIGWINCH handler while curses is initialised.

    Ncurses then leaves SIGWINCH to the loop,
    and the previous handler is restored afterwards.
    """
    if not hasattr(signal, "SIGWINCH"):
        yield
        return
    previous = signal.signal(signal.SIGWINCH, _ignore_signal)
    try:
        yield
    finally:
        # Python cannot restore a handler installed outside it.
        signal.signal(
            signal.SIGWINCH,
            signal.SIG_DFL if previous is None else previous,
        )


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


def main() -> int:
    """Show keys, a clock and thread wakeups, to check a terminal."""

    async def show() -> None:
        loop = typing.cast(EventLoop, asyncio.get_event_loop())
        window = loop.window
        keys = collections.deque(maxlen=8)  # type: typing.Deque[str]
        counts = collections.Counter()  # type: typing.Counter[str]

        def draw() -> None:
            height, width = window.getmaxyx()
            lines = [
                "Selector loop check. q quits, Ctrl+C interrupts,",
                "t wakes the loop from a thread after 0.5 s.",
                "",
                "Time {}".format(time.strftime("%H:%M:%S")),
                "Size {} x {}".format(height, width),
                "Keys {}: {}".format(counts["keys"], " ".join(keys)),
                "Resizes {}".format(counts["resizes"]),
                "Thread wakeups {} of {}".format(
                    counts["woken"], counts["requested"]
                ),
            ]
            window.erase()
            for row, line in enumerate(lines[: height - 1]):
                window.addnstr(row, 0, line, width - 1)
            window.refresh()

        def woken() -> None:
            counts["woken"] += 1
            draw()

        async def tick() -> None:
            while True:
                draw()
                await asyncio.sleep(1 - time.time() % 1)

        ticker = loop.create_task(tick())
        try:
            while True:
                key = await loop.getch()
                if key == ord("q"):
                    return
                if key == curses.KEY_RESIZE:
                    counts["resizes"] += 1
                if key == ord("t"):
                    counts["requested"] += 1
                    threading.Timer(
                        0.5, loop.call_soon_threadsafe, [woken]
                    ).start()
                counts["keys"] += 1
                keys.append(curses.keyname(key).decode(errors="replace"))
                draw()
        finally:
            ticker.cancel()

    try:
        run(show())
    except KeyboardInterrupt:
        print("Interrupted.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
