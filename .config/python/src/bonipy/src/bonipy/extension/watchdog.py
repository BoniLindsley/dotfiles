#!/usr/bin/env python3

# ~/.local/lib/python/venv/default/lib/python3.11/site-packages/watchdog/observers/inotify_buffer.py"

import asyncio
from collections import abc
import contextlib
import logging
import sys
import typing as t

# External dependencies.
import watchdog.events
import watchdog.observers
import watchdog.observers.api


_P = t.ParamSpec("_P")
_T = t.TypeVar("_T")
logger = logging.getLogger(__name__)


class AsyncEventQueue(t.Generic[_T]):
    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._async_queue = asyncio.Queue[_T]()
        self._cached_item: None | _T = None
        self._running_loop = asyncio.get_running_loop()

    # Wait until queue has items, but do not remove from queue.
    # The default `asyncio.Queue` does not have this interface.
    # So keep the returned item.
    async def async_wait(self) -> None:
        if self._cached_item is None:
            self._cached_item = await self._async_queue.get()

    def get(self, block: bool = False) -> _T:
        # The non-blocking version is not used.
        if not block:
            raise NotImplementedError("Non-blocking AsyncEventQueue.get not supported.")
        if self._cached_item is not None:
            item = self._cached_item
            self._cached_item = None
            return item
        return self._async_queue.get_nowait()

    def put(self, item: _T) -> None:
        # Called by emitters in separate threads.
        # So this method must be thread-safe. The only thread-safe one.
        self._running_loop.call_soon_threadsafe(self._async_queue.put_nowait, item)

    def task_done(self) -> None:
        self._async_queue.task_done()


EventWatch = tuple[
    watchdog.events.FileSystemEvent, watchdog.observers.api.ObservedWatch
]


class Feed(t.Generic[_T]):
    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._item: asyncio.Future[tuple[_T, "Feed[_T]"]]
        self._item = asyncio.get_running_loop().create_future()

    async def get(self) -> tuple[_T, "Feed[_T]"]:
        return await self._item

    def set(self, value: _T) -> "Feed[_T]":
        next_item: Feed[_T] = Feed()
        self._item.set_result((value, next_item))
        return next_item


class Subscriber(t.Generic[_T]):
    def __init__(self, feed: Feed[_T], *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        # WARNING: Make sure `feed` argument is `del` after initialisation.
        # This reduces reference count, so that old feeds can be garbage collected.
        self._feed = feed

    async def read(self) -> abc.AsyncIterator[_T]:
        while True:
            value, self._feed = await self._feed.get()
            yield value


class Publisher(t.Generic[_T]):
    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._feed: Feed[_T] = Feed()

    def subscribe(self) -> Subscriber[_T]:
        return Subscriber(self._feed)

    def write(self, value: _T) -> None:
        self._feed = self._feed.set(value)


class AsyncEventDispatcher(watchdog.observers.api.EventDispatcher):
    dispatch_events: abc.Callable[[AsyncEventQueue[EventWatch]], None]

    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[no-untyped-call]
        # Events to be dispatched inside asyncio event loop.
        self._event_queue: AsyncEventQueue[EventWatch]  # type: ignore[assignment]
        self._event_queue = AsyncEventQueue()
        # Override with asyncio version deliberately.
        self._stopped_event = asyncio.Event()  # type: ignore[assignment]

    async def async_dispatch_events(self) -> None:
        while True:
            await self._event_queue.async_wait()
            self.dispatch_events(self._event_queue)

    # Override `BaseObserver.start` to be noop.
    def start(self) -> None:
        pass


class BaseAsyncObserver(watchdog.observers.api.BaseObserver, AsyncEventDispatcher):
    on_thread_stop: abc.Callable[[], None]

    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[no-untyped-call]
        # Just pass through all attempts to lock. Not needed in asyncio.
        self._lock: contextlib.AbstractContextManager[None]  # type: ignore[assignment]
        self._lock = contextlib.nullcontext()

    async def async_run(self) -> None:
        # Run super class `start()`, which calls its subclass `start()`.
        # It expected to start a thread, but here it is overridden to do nothing,
        # in order to return immediately.
        self.start()
        try:
            await self.async_dispatch_events()
        finally:
            self.on_thread_stop()

    # Provide type hint.
    def schedule(  # pylint: disable=useless-parent-delegation
        self,
        event_handler: watchdog.events.FileSystemEventHandler,
        path: str,
        recursive: bool = False,
    ) -> watchdog.observers.api.ObservedWatch:
        return super().schedule(  # type: ignore[no-any-return, no-untyped-call]
            event_handler, path, recursive
        )

    # Override `BaseObserver.start` to be noop.
    def start(self) -> None:
        pass


# Check: Not a static deducible type in watchdog.
# https://github.com/gorakhargosh/watchdog/issues/982
class Observer(watchdog.observers.Observer, BaseAsyncObserver):  # type: ignore[misc,valid-type]
    pass


class PrintHandler(watchdog.events.FileSystemEventHandler):
    def dispatch(self, event: watchdog.events.FileSystemEvent) -> None:
        print("OK:", event)


async def amain() -> int:
    observer = Observer()
    event_handler = PrintHandler()
    observer.schedule(event_handler, "/home/boni/tmp")
    await observer.async_run()
    return 0


def main() -> int:
    logging.basicConfig(level=logging.DEBUG)
    try:
        return asyncio.run(amain())
    except KeyboardInterrupt:
        return 2  # SIGINT = 2


if __name__ == "__main__":
    sys.exit(main())
