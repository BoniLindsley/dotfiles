#!/usr/bin/env python3

# Standard libraries.
import asyncio
import collections.abc as cabc
import typing as t


_P = t.ParamSpec("_P")
_T = t.TypeVar("_T")


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

    def stop(self) -> None:
        self._item.cancelled()


class Subscriber(t.Generic[_T]):
    def __init__(self, feed: Feed[_T], *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        # WARNING: Make sure `feed` argument is `del` after initialisation.
        # This reduces reference count, so that old feeds can be garbage collected.
        self._feed = feed

    async def read(self) -> cabc.AsyncIterator[_T]:
        while True:
            try:
                value, self._feed = await self._feed.get()
            except asyncio.CancelledError:
                break
            yield value


class Publisher(t.Generic[_T]):
    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._feed: Feed[_T] = Feed()

    def stop(self) -> None:
        self._feed.stop()

    def subscribe(self) -> Subscriber[_T]:
        return Subscriber(self._feed)

    def write(self, value: _T) -> None:
        self._feed = self._feed.set(value)
