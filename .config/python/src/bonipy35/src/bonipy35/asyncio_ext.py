#!/usr/bin/env python3

# Standard libraries.
import asyncio
import sys
import typing

from typing import Tuple, Union

_T = typing.TypeVar("_T")


class Feed(typing.Generic[_T]):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._item = asyncio.Future(
            loop=asyncio.get_event_loop()
        )  # type: asyncio.Future[Union[None, Tuple[_T, Feed[_T]]]]

    async def get(self) -> "Union[None, Tuple[_T, Feed[_T]]]":
        # Each subscriber shares this future; cancellation must stay local.
        return await asyncio.shield(self._item)

    def set(self, value: _T) -> "Feed[_T]":
        next_item = Feed()  # type: Feed[_T]
        self._item.set_result((value, next_item))
        return next_item

    def stop(self) -> None:
        if not self._item.done():
            self._item.set_result(None)


class Subscriber(typing.Generic[_T]):
    def __init__(
        self, feed: Feed[_T], *args: typing.Any, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._feed = feed

    def __aiter__(self) -> "typing.Self":
        return self

    async def __anext__(self) -> _T:
        item = await self._feed.get()
        if item is None:
            raise StopAsyncIteration
        value, self._feed = item
        return value

    def read(self) -> "Subscriber[_T]":
        return self


class Publisher(typing.Generic[_T]):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._feed = Feed()  # type: Feed[_T]

    def stop(self) -> None:
        self._feed.stop()

    def subscribe(self) -> Subscriber[_T]:
        return Subscriber(self._feed)

    def write(self, value: _T) -> None:
        self._feed = self._feed.set(value)


class _StdinReadyIterator:
    def __init__(self) -> None:
        self._closed = False
        self._pending = None  # type: Union[None, asyncio.Future[None]]

    def __aiter__(self) -> "typing.Self":
        return self

    async def __anext__(self) -> None:
        if self._closed:
            raise StopAsyncIteration
        self._pending = stdin_ready()
        try:
            await self._pending
        finally:
            self._pending = None

    async def aclose(self) -> None:
        self._closed = True
        if self._pending is not None:
            self._pending.cancel()


def loop_stdin_ready() -> _StdinReadyIterator:
    return _StdinReadyIterator()


def stdin_ready() -> "asyncio.Future[None]":
    """Wait for stdin readability without consuming input.

    The caller must exclusively own stdin's reader registration on this loop.
    """
    loop = asyncio.get_event_loop()
    stdin_fd = sys.stdin.fileno()
    future = asyncio.Future(loop=loop)  # type: asyncio.Future[None]

    def ready() -> None:
        # Unread input stays readable, so unregister for a single notification.
        loop.remove_reader(stdin_fd)
        if not future.done():
            future.set_result(None)

    def cleanup(completed: "asyncio.Future[None]") -> None:
        if completed.cancelled():
            loop.remove_reader(stdin_fd)

    loop.add_reader(stdin_fd, ready)
    future.add_done_callback(cleanup)
    return future


def _run_legacy(coro: "typing.Coroutine[typing.Any, typing.Any, _T]") -> _T:
    """Provide runner cleanup on Python versions predating asyncio.run."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # Python 3.5 stores in `Task` instead of `asyncio`.
        all_tasks = getattr(asyncio, "all_tasks", None)
        if all_tasks is None:
            all_tasks = getattr(asyncio.Task, "all_tasks")
        pending = list(all_tasks(loop))
        for task in pending:
            task.cancel()
        try:
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            for task in pending:
                if not task.cancelled() and task.exception() is not None:
                    loop.call_exception_handler(
                        {
                            "message": "Exception during asyncio shutdown",
                            "exception": task.exception(),
                            "task": task,
                        }
                    )
        finally:
            try:
                loop.close()
            finally:
                asyncio.set_event_loop(None)


def run(coro: "typing.Coroutine[typing.Any, typing.Any, _T]") -> _T:
    """Run a coroutine using asyncio.run, with a Python 3.5/3.6 fallback.

    Use the installed event-loop policy. Cancel unfinished tasks and close the
    loop on exit. Call outside an existing running loop.
    """
    runner = getattr(asyncio, "run", None)
    if runner is not None:
        return typing.cast(_T, runner(coro))
    return _run_legacy(coro)
