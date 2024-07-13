#!/usr/bin/env python3

import asyncio
import contextlib
import logging
import pathlib
import typing

from collections.abc import AsyncIterator

# External dependencies.
import watchdog.events
import watchdog.observers
import watchdog.observers.api

_P = typing.ParamSpec("_P")
_T = typing.TypeVar("_T")
_U = typing.TypeVar("_U")

_logger = logging.getLogger(__name__)


class PubSub(typing.Generic[_T]):
    Message = asyncio.Future["tuple[_U, Message[_U]]"]

    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._item = self.create_message()

    @classmethod
    def create_message(cls) -> "PubSub.Message[_T]":
        return asyncio.get_running_loop().create_future()

    def publish(self, value: _T) -> None:
        next_item = self.create_message()
        self._item.set_result((value, next_item))
        self._item = next_item

    def stop(self) -> None:
        self._item.cancel()

    async def subscribe(self) -> AsyncIterator[_T]:
        next_item = self._item
        while True:
            try:
                value, next_item = await next_item
            except asyncio.CancelledError:
                break
            yield value


class PubSubEventQueue:
    def __init__(  # type: ignore[valid-type]
        self,
        *args: _P.args,
        pubsub: PubSub[watchdog.events.FileSystemEvent],
        **kwargs: _P.kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._pubsub = pubsub
        self._running_loop = asyncio.get_running_loop()

    def put(
        self,
        item: "tuple[watchdog.events.FileSystemEvent, watchdog.observers.api.ObservedWatch]",
    ) -> None:
        # Called by emitters in separate threads.
        # So this method must be thread-safe. The only thread-safe one.
        self._running_loop.call_soon_threadsafe(self._pubsub.publish, item[0])


def get_default_emitter_class() -> "type[watchdog.observers.api.EventEmitter]":
    # pylint: disable=protected-access
    observer = watchdog.observers.Observer()
    return observer._emitter_class  # type: ignore[no-any-return]


@contextlib.asynccontextmanager
async def schedule(
    *,
    path: pathlib.Path,
    emitter_class: "None | type[watchdog.observers.api.EventEmitter]" = None,
    recursive: bool = False,
    timeout: float = watchdog.observers.api.DEFAULT_EMITTER_TIMEOUT
) -> AsyncIterator[PubSub[watchdog.events.FileSystemEvent]]:
    if emitter_class is None:
        emitter_class = get_default_emitter_class()

    pubsub = PubSub()  # type: PubSub[watchdog.events.FileSystemEvent]
    try:
        emitter = emitter_class(
            event_queue=PubSubEventQueue(pubsub=pubsub),
            watch=watchdog.observers.api.ObservedWatch(  # type: ignore[no-untyped-call]
                str(path), recursive
            ),
            timeout=timeout,
        )
        emitter.start()  # type: ignore[no-untyped-call]
        try:
            yield pubsub
        finally:
            emitter.stop()  # type: ignore[no-untyped-call]
            try:
                emitter.join()
            except RuntimeError:
                _logger.warning("Failed to join emitter thread.")
    finally:
        pubsub.stop()
