#!/usr/bin/env python3

# Standard libraries.
import asyncio
import collections.abc as cabc
import sys
import typing

_T = typing.TypeVar("_T")

# TODO: async generators is 3.6.
# Consider reimplementing using `__aiter__` and `__anext__`.


class Feed(typing.Generic[_T]):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._item = (
            asyncio.get_running_loop().create_future()
        )  # type: asyncio.Future[tuple[_T, "Feed[_T]"]]

    async def get(self) -> "tuple[_T, Feed[_T]]":
        return await self._item

    def set(self, value: _T) -> "Feed[_T]":
        next_item = Feed()  # type: Feed[_T]
        self._item.set_result((value, next_item))
        return next_item

    def stop(self) -> None:
        self._item.cancelled()


class Subscriber(typing.Generic[_T]):
    def __init__(self, feed: Feed[_T], *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        # WARNING: Make sure `feed` argument is `del` after initialisation.
        # This reduces reference count, so that old feeds can be garbage collected.
        self._feed = feed

    async def read(self) -> "cabc.AsyncIterator[_T]":
        while True:
            try:
                value, self._feed = await self._feed.get()
            except asyncio.CancelledError:
                break
            yield value


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


async def loop_stdin_ready() -> "cabc.AsyncIterator[None]":
    loop = asyncio.get_running_loop()
    stdin_fd = sys.stdin.fileno()
    while True:
        future = loop.create_future()  # type: asyncio.Future[None]
        loop.add_reader(stdin_fd, future.set_result, None)
        await future
        yield


def stdin_ready() -> "asyncio.Future[None]":
    loop = asyncio.get_running_loop()
    future = loop.create_future()  # type: asyncio.Future[None]
    loop.add_reader(sys.stdin.fileno(), future.set_result, None)
    return future
