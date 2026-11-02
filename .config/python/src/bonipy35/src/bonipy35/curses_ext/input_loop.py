#!/usr/bin/env python3
"""Curses input through a stock asyncio selector loop, without polling.

The loop waits in its selector, never inside curses.
Terminal input is one more readable file descriptor,
and an input selector also reports it ready
while curses holds keys that the descriptor no longer shows,
such as pushed back keys and `KEY_RESIZE`.
Applications read keys themselves, with nodelay ``getch``,
and wait with an `InputWaiter` when there is none.

Set up curses with `initialise`, run the application on an `EventLoop`
and read keys with a `WindowInput`::

    async def main(window):
        window_input = WindowInput(window)
        key = await window_input.getch()

    with initialise() as window:
        asyncio_ext.run(main(window), loop_factory=EventLoop)

`run` does the last two steps: ``run(main)``.

On Unix, the loop resizes curses on SIGWINCH.
On Windows, where selectors wait on sockets only,
it waits on the console input too,
and windows-curses resizes curses itself before returning `KEY_RESIZE`.

Run ``python -m bonipy35.curses_ext.input_loop`` to check a terminal.
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
import socket
import sys
import threading
import time
import typing

from typing import Callable, Iterator, List, Tuple, Union

# Internal modules.
from .. import asyncio_ext
from . import raii

_T = typing.TypeVar("_T")


# A mixin: a concrete selector later in the MRO implements the rest.
# pylint: disable-next=abstract-method
class InputSelectorMixin(selectors.BaseSelector):
    """Report ``input_fd`` readable while ``window`` holds a key.

    Registering ``input_fd`` for reading means someone waits for input.
    Then each select first peeks with ``getch`` and ``ungetch``,
    so ``window`` must be in nodelay mode.
    Without that registration, curses is not touched.
    ``window`` defaults to ``stdscr``, so curses must be initialised.
    """

    def __init__(
        self,
        *args: typing.Any,
        window: Union[None, "curses.window"] = None,
        input_fd: int = 0,
        **kwargs: typing.Any
    ) -> None:
        if window is None:
            window = _stdscr()
        super().__init__(*args, **kwargs)
        self._window = window
        self._input_fd = input_fd

    @property
    def input_fd(self) -> int:
        return self._input_fd

    def select(
        self, timeout: Union[None, float] = None
    ) -> List[Tuple[selectors.SelectorKey, int]]:
        input_key = self.get_map().get(self._input_fd)
        if input_key is None or not input_key.events & selectors.EVENT_READ:
            return self._wait(timeout, None)
        if self._has_key():
            return _with_input(super().select(0), input_key)
        return self._wait(timeout, input_key)

    def _wait(
        self,
        timeout: Union[None, float],
        input_key: Union[None, selectors.SelectorKey],
    ) -> List[Tuple[selectors.SelectorKey, int]]:
        """Wait for events while curses holds no key.

        ``input_key`` is given if ``input_fd`` is registered for reading.
        """
        del input_key
        return super().select(timeout)

    def _has_key(self) -> bool:
        key = self._window.getch()
        if key == -1:
            return False
        curses.ungetch(key)
        return True


class InputSelector(InputSelectorMixin, selectors.DefaultSelector):
    pass


def _with_input(
    ready: List[Tuple[selectors.SelectorKey, int]],
    input_key: selectors.SelectorKey,
) -> List[Tuple[selectors.SelectorKey, int]]:
    """Return ``ready`` with ``input_key`` readable."""
    for index, (key, events) in enumerate(ready):
        if key.fd == input_key.fd:
            ready[index] = (key, events | selectors.EVENT_READ)
            return ready
    ready.append((input_key, selectors.EVENT_READ))
    return ready


def _stdscr() -> "curses.window":
    """Return ``stdscr`` of initialised curses, refreshing it."""
    # Raises before the first initscr, which would set up the terminal.
    if curses.isendwin():
        raise curses.error("curses has ended")
    # Curses is initialised, so initscr only returns stdscr.
    return curses.initscr()


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
            # The event first, so that waits may leave out the input.
            self._handles = (wintypes.HANDLE * 2)(self._event, console_input)

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

        def wait(self, timeout: Union[None, float], with_input: bool) -> None:
            """Wait on the event, and on the input if ``with_input``."""
            milliseconds = (
                _INFINITE
                if timeout is None
                else min(_INFINITE - 1, max(0, math.ceil(timeout * 1000)))
            )
            if (
                self._kernel32.WaitForMultipleObjects(
                    2 if with_input else 1, self._handles, False, milliseconds
                )
                == _WAIT_FAILED
            ):
                raise ctypes.WinError(ctypes.get_last_error())

        def close(self) -> None:
            if self._event:
                self._kernel32.CloseHandle(self._event)
                self._event = None


def _new_console() -> typing.Any:
    """Return the console of standard input to wait on."""
    if sys.platform == "win32":  # pragma: no cover
        return _Console()
    raise RuntimeError("Only Windows has a console to wait on")


def _fd_of(fileobj: typing.Any) -> Union[None, int]:
    """Return the file descriptor of ``fileobj``, or None if invalid."""
    if isinstance(fileobj, int):
        return fileobj
    try:
        return int(fileobj.fileno())
    except (AttributeError, TypeError, ValueError):
        return None


class _InputMap(typing.Mapping[typing.Any, selectors.SelectorKey]):
    """The keys in ``inner``, and ``input_key``, which is not in it."""

    def __init__(
        self,
        inner: typing.Mapping[typing.Any, selectors.SelectorKey],
        input_key: selectors.SelectorKey,
    ) -> None:
        self._inner = inner
        self._input_key = input_key

    def __len__(self) -> int:
        return len(self._inner) + 1

    def __getitem__(self, fileobj: typing.Any) -> selectors.SelectorKey:
        if _fd_of(fileobj) == self._input_key.fd:
            return self._input_key
        return self._inner[fileobj]

    def __iter__(self) -> Iterator[typing.Any]:
        yield from self._inner
        yield self._input_key.fd


class ConsoleSelectorMixin(InputSelectorMixin):
    """Wait on a Windows console for ``input_fd``, and on sockets.

    Windows selectors wait on sockets only,
    so ``input_fd`` only names the console input:
    its registration stays out of the selector this is mixed into,
    and only while it lasts does the wait include the console input.
    Other registered sockets are bound to an event of ``console``.
    It signals only network events after binding or a reset,
    so readiness is checked before each wait as well as after.
    ``console`` defaults to standard input's,
    and closes with the selector.
    """

    def __init__(
        self,
        *args: typing.Any,
        console: typing.Any = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._console = _new_console() if console is None else console
        self._input_key = None  # type: Union[None, selectors.SelectorKey]

    def register(
        self, fileobj: typing.Any, events: int, data: typing.Any = None
    ) -> selectors.SelectorKey:
        if _fd_of(fileobj) != self.input_fd:
            key = super().register(fileobj, events, data)
            try:
                self._console.bind(key.fd, events)
            except BaseException:
                super().unregister(fileobj)
                raise
            return key
        if events != selectors.EVENT_READ:
            raise ValueError("{!r} is for reading only".format(fileobj))
        if self._input_key is not None:
            raise KeyError("{!r} is already registered".format(fileobj))
        self._input_key = selectors.SelectorKey(
            fileobj, self.input_fd, events, data
        )
        return self._input_key

    def unregister(self, fileobj: typing.Any) -> selectors.SelectorKey:
        if _fd_of(fileobj) != self.input_fd:
            key = super().unregister(fileobj)
            self._console.unbind(key.fd)
            return key
        if self._input_key is None:
            raise KeyError("{!r} is not registered".format(fileobj))
        key, self._input_key = self._input_key, None
        return key

    def modify(
        self, fileobj: typing.Any, events: int, data: typing.Any = None
    ) -> selectors.SelectorKey:
        if _fd_of(fileobj) != self.input_fd:
            key = super().modify(fileobj, events, data)
            self._console.bind(key.fd, events)
            return key
        if self._input_key is None:
            raise KeyError("{!r} is not registered".format(fileobj))
        if events != self._input_key.events:
            raise ValueError("{!r} is for reading only".format(fileobj))
        self._input_key = self._input_key._replace(data=data)
        return self._input_key

    def get_map(self) -> typing.Mapping[typing.Any, selectors.SelectorKey]:
        inner = super().get_map()
        # A closed selector has no map.
        if inner is None or self._input_key is None:
            return inner
        return _InputMap(inner, self._input_key)

    def close(self) -> None:
        self._input_key = None
        try:
            super().close()
        finally:
            self._console.close()

    def _wait(
        self,
        timeout: Union[None, float],
        input_key: Union[None, selectors.SelectorKey],
    ) -> List[Tuple[selectors.SelectorKey, int]]:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            # Network events after this check signal the event again.
            self._console.reset()
            ready = super()._wait(0, input_key)
            remaining = (
                None if deadline is None else deadline - time.monotonic()
            )
            if ready or (remaining is not None and remaining <= 0):
                return ready
            self._console.wait(remaining, with_input=input_key is not None)
            if input_key is not None and self._has_key():
                return _with_input(super()._wait(0, input_key), input_key)
            # Otherwise sockets are ready, the time is up,
            # or curses drained console events that were not keys.


class ConsoleSelector(ConsoleSelectorMixin, selectors.SelectSelector):
    pass


class InputWaiter:
    """Wait on ``loop`` for curses input on ``input_fd``.

    The loop's selector must be an input selector for ``input_fd``.
    One reader is registered while anyone waits, and removed on wakeup,
    so unread input does not wake the loop while no one waits.
    """

    def __init__(
        self, loop: asyncio.AbstractEventLoop, *, input_fd: int = 0
    ) -> None:
        self._loop = loop
        self._input_fd = input_fd
        self._futures = []  # type: List[asyncio.Future[None]]
        self._registered = False

    async def input_ready(self) -> None:
        """Return when input may be ready, or on `wake()`.

        Readiness is a hint: read with nodelay ``getch`` and wait again
        if it returns -1.
        """
        future = asyncio.Future(loop=self._loop)  # type: asyncio.Future[None]
        self._futures.append(future)
        if not self._registered:
            self._loop.add_reader(self._input_fd, self.wake)
            self._registered = True
        try:
            await future
        finally:
            if future in self._futures:
                self._futures.remove(future)
            if not self._futures:
                self._unregister()

    def wake(self) -> None:
        """Return from every pending `input_ready()`."""
        futures, self._futures = self._futures, []
        for future in futures:
            if not future.done():
                future.set_result(None)
        self._unregister()

    def _unregister(self) -> None:
        if self._registered:
            self._loop.remove_reader(self._input_fd)
            self._registered = False


class WindowInput:
    """Read keys of ``window`` on the running loop.

    The loop must have an ``input_selector`` property
    giving its input selector, as `EventLoop` does.
    ``window`` must be in nodelay mode.
    ``waiter`` waits for input on the selector's ``input_fd``;
    `wake()` it to return from a pending `getch()` early.
    """

    def __init__(self, window: "curses.window") -> None:
        loop = asyncio.get_event_loop()
        selector = getattr(loop, "input_selector", None)
        if not isinstance(selector, InputSelectorMixin):
            raise TypeError(
                "Expected a loop with an input_selector, got {!r}".format(
                    loop
                )
            )
        self.window = window
        self.waiter = InputWaiter(loop, input_fd=selector.input_fd)

    async def getch(self) -> int:
        """Return the next key, waiting for one."""
        while True:
            key = self.window.getch()
            if key != -1:
                return key
            await self.waiter.input_ready()


def _resize() -> None:
    """Resize curses to the terminal, queueing `KEY_RESIZE` on a change."""
    try:
        columns, lines = os.get_terminal_size()
    except OSError:
        return
    curses.resizeterm(lines, columns)


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


class UnixEventLoop(asyncio.SelectorEventLoop):
    """Report curses input on standard input, peeking through ``stdscr``.

    ``selector`` replaces that default input selector.
    Terminal size changes queue `KEY_RESIZE`.
    Create on the main thread, while curses is initialised.
    """

    def __init__(
        self, selector: Union[None, InputSelectorMixin] = None
    ) -> None:
        super().__init__(InputSelector() if selector is None else selector)
        if hasattr(signal, "SIGWINCH"):
            # Closing the loop removes the handler.
            self.add_signal_handler(signal.SIGWINCH, _resize)

    @property
    def input_selector(self) -> InputSelectorMixin:
        # Asyncio keeps the selector given above, but only privately.
        return typing.cast(
            InputSelectorMixin, self._selector  # type: ignore[attr-defined]
        )


class WindowsEventLoop(asyncio.SelectorEventLoop):
    """Report curses input on the console, peeking through ``stdscr``.

    ``selector`` replaces that default console selector.
    Until the loop closes, signals such as Ctrl+C end its waits:
    its own socket pair is the signal wakeup file descriptor.
    Create on the main thread, while curses is initialised.
    """

    def __init__(
        self, selector: Union[None, ConsoleSelectorMixin] = None
    ) -> None:
        super().__init__(ConsoleSelector() if selector is None else selector)
        self._wakeup_reader, self._wakeup_writer = socket.socketpair()
        self._wakeup_reader.setblocking(False)
        self._wakeup_writer.setblocking(False)
        self.add_reader(self._wakeup_reader.fileno(), self._drain_wakeups)
        self._previous_wakeup_fd = signal.set_wakeup_fd(
            self._wakeup_writer.fileno()
        )

    @property
    def input_selector(self) -> ConsoleSelectorMixin:
        # Asyncio keeps the selector given above, but only privately.
        return typing.cast(
            ConsoleSelectorMixin, self._selector  # type: ignore[attr-defined]
        )

    def _drain_wakeups(self) -> None:
        # The writer stays open while this is registered.
        try:
            while True:
                self._wakeup_reader.recv(4096)
        except BlockingIOError:
            pass

    def close(self) -> None:
        if self.is_running():
            raise RuntimeError("Cannot close a running event loop")
        if self.is_closed():
            return
        try:
            signal.set_wakeup_fd(self._previous_wakeup_fd)
            self.remove_reader(self._wakeup_reader.fileno())
        finally:
            super().close()
            self._wakeup_reader.close()
            self._wakeup_writer.close()


if sys.platform == "win32":  # pragma: no cover
    EventLoop = WindowsEventLoop
else:
    EventLoop = UnixEventLoop


@contextlib.contextmanager
def initialise(
    initscr: Union[None, Callable[[], "curses.window"]] = None,
) -> Iterator["curses.window"]:
    """Set up curses for an `EventLoop`, yielding ``stdscr``.

    Create the loop inside, so that SIGWINCH is left to it.
    ``stdscr`` is in nodelay mode until exit.
    Restores the terminal and the SIGWINCH handler even on exceptions.
    """
    with keep_resize_handler():
        with raii.initialise(initscr=initscr) as window:
            window.nodelay(True)
            try:
                yield window
            finally:
                window.nodelay(False)


def run(
    func: Callable[
        ["curses.window"], "typing.Coroutine[typing.Any, typing.Any, _T]"
    ],
) -> _T:
    """Return ``func(stdscr)`` run on an `EventLoop` inside `initialise`.

    Restores the terminal on exit and cancels unfinished tasks.
    """
    with initialise() as window:
        return asyncio_ext.run(func(window), loop_factory=EventLoop)


def main() -> int:
    """Show input, a clock and thread wakeups, to check a terminal."""

    async def show(window: "curses.window") -> None:
        loop = asyncio.get_event_loop()
        window_input = WindowInput(window)
        keys = collections.deque(maxlen=8)  # type: typing.Deque[str]
        counts = collections.Counter()  # type: typing.Counter[str]
        mouse = ""
        curses.mousemask(curses.ALL_MOUSE_EVENTS)

        def draw() -> None:
            height, width = window.getmaxyx()
            lines = [
                "Input loop check. q quits, Ctrl+C interrupts,",
                "t wakes the loop from a thread after 0.5 s.",
                "",
                "Time {}".format(time.strftime("%H:%M:%S")),
                "Size {} x {}".format(height, width),
                "Keys {}: {}".format(counts["keys"], " ".join(keys)),
                "Resizes {}".format(counts["resizes"]),
                "Mouse events {}: {}".format(counts["mouse"], mouse),
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

        ticker = asyncio.ensure_future(tick())
        try:
            while True:
                key = await window_input.getch()
                if key == ord("q"):
                    return
                if key == curses.KEY_RESIZE:
                    counts["resizes"] += 1
                if key == curses.KEY_MOUSE:
                    counts["mouse"] += 1
                    try:
                        _, x, y, _, state = curses.getmouse()
                        mouse = "{}, {} state {:#x}".format(x, y, state)
                    except curses.error:
                        mouse = "unreadable"
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
        run(show)
    except KeyboardInterrupt:
        print("Interrupted.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
