#!/usr/bin/env python3
"""Curses input through a stock asyncio selector loop, without polling.

The loop waits in its selector, never inside curses.
Terminal input is one more readable file descriptor,
and an input selector also reports it ready
while curses holds keys that the descriptor no longer shows,
such as pushed back keys and `KEY_RESIZE`.
Applications read keys themselves, with nodelay ``getch``,
and wait with an `InputWaiter` when there is none.

Unix only for now: Windows selectors cannot wait on the console.
"""

# Standard libraries.
import asyncio
import contextlib
import curses
import functools
import os
import selectors
import signal
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
    """

    def __init__(
        self,
        *args: typing.Any,
        window: "curses.window",
        input_fd: int = 0,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._window = window
        self._input_fd = input_fd

    def select(
        self, timeout: Union[None, float] = None
    ) -> List[Tuple[selectors.SelectorKey, int]]:
        input_key = self.get_map().get(self._input_fd)
        if (
            input_key is None
            or not input_key.events & selectors.EVENT_READ
            or not self._has_key()
        ):
            return super().select(timeout)
        ready = super().select(0)
        for index, (key, events) in enumerate(ready):
            if key.fd == input_key.fd:
                ready[index] = (key, events | selectors.EVENT_READ)
                return ready
        ready.append((input_key, selectors.EVENT_READ))
        return ready

    def _has_key(self) -> bool:
        key = self._window.getch()
        if key == -1:
            return False
        curses.ungetch(key)
        return True


class InputSelector(InputSelectorMixin, selectors.DefaultSelector):
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


async def getch(window: "curses.window", waiter: InputWaiter) -> int:
    """Return the next key of ``window``, which must be in nodelay mode."""
    while True:
        key = window.getch()
        if key != -1:
            return key
        await waiter.input_ready()


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


def _new_loop(window: "curses.window") -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(InputSelector(window=window))


async def _main(
    func: "Callable[[curses.window, InputWaiter], typing.Awaitable[_T]]",
    window: "curses.window",
) -> _T:
    loop = asyncio.get_event_loop()
    if hasattr(signal, "SIGWINCH"):
        # Closing the loop removes the handler.
        loop.add_signal_handler(signal.SIGWINCH, _resize)
    return await func(window, InputWaiter(loop))


def run(
    func: "Callable[[curses.window, InputWaiter], typing.Awaitable[_T]]",
) -> _T:
    """Run ``func(window, waiter)`` with curses on standard input.

    ``window`` is in nodelay mode while ``func`` runs,
    and ``waiter`` waits for its input.
    Terminal size changes queue `KEY_RESIZE`.
    Restores the terminal and the SIGWINCH handler even on exceptions.
    Unfinished tasks are cancelled and awaited.
    Keep curses calls on the main thread;
    worker threads submit them with ``call_soon_threadsafe``.
    """
    with keep_resize_handler():
        with raii.initialise() as window:
            window.nodelay(True)
            try:
                return asyncio_ext.run(
                    _main(func, window),
                    loop_factory=functools.partial(_new_loop, window),
                )
            finally:
                window.nodelay(False)
