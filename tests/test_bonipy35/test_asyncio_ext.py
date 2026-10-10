#!/usr/bin/env python3

# Standard libraries.
import ast
import asyncio
import os
from pathlib import Path
from typing import Iterator, Tuple

# External dependencies.
import pytest

# Internal modules.
from bonipy35.asyncio_ext import (
    Feed,
    Publisher,
    Subscriber,
    loop_stdin_ready,
    run,
    stdin_ready,
)


@pytest.fixture(name="event_loop")
def fixture_event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture(name="stdin_pipe")
def fixture_stdin_pipe(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Tuple[int, int]]:
    read_fd, write_fd = os.pipe()
    with os.fdopen(read_fd, "rb") as stream:
        monkeypatch.setattr("sys.stdin", stream)
        try:
            yield read_fd, write_fd
        finally:
            os.close(write_fd)


class TestFeed:
    def test_value_and_stop(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> None:
        feed: Feed[int] = Feed()
        next_feed = feed.set(42)
        assert event_loop.run_until_complete(feed.get()) == (42, next_feed)
        feed.stop()
        next_feed.stop()
        next_feed.stop()  # Should be idempotent.
        assert event_loop.run_until_complete(next_feed.get()) is None


class TestSubscriber:
    def test_async_for(self, event_loop: asyncio.AbstractEventLoop) -> None:
        async def check() -> None:
            feed: Feed[int] = Feed()
            subscriber = Subscriber(feed)
            feed.set(1).set(2).stop()
            values = []
            async for value in subscriber:
                values.append(value)
            assert values == [1, 2]

        event_loop.run_until_complete(asyncio.wait_for(check(), timeout=1))


class TestPublisher:
    def test_broadcast_and_shutdown(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> None:
        async def check() -> None:
            publisher: Publisher[int] = Publisher()
            first, second = publisher.subscribe(), publisher.subscribe()
            publisher.write(1)
            publisher.write(2)
            publisher.stop()
            publisher.stop()  # Should be idempotent.
            assert [value async for value in first.read()] == [1, 2]
            assert [value async for value in second.read()] == [1, 2]
            assert [
                value async for value in publisher.subscribe().read()
            ] == []
            with pytest.raises(asyncio.InvalidStateError):
                publisher.write(3)

        event_loop.run_until_complete(check())

    def test_cancellation_is_local(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> None:
        async def check() -> None:
            publisher: Publisher[int] = Publisher()
            first, second = publisher.subscribe(), publisher.subscribe()
            cancelled = event_loop.create_task(anext(first))
            waiting = event_loop.create_task(anext(second))
            await asyncio.sleep(0)
            cancelled.cancel()
            with pytest.raises(asyncio.CancelledError):
                await cancelled
            publisher.write(7)
            assert await asyncio.wait_for(waiting, timeout=1) == 7
            assert await anext(first) == 7
            publisher.stop()

        event_loop.run_until_complete(check())

    def test_stop_wakes_waiting_readers(
        self, event_loop: asyncio.AbstractEventLoop
    ) -> None:
        async def check() -> None:
            publisher: Publisher[int] = Publisher()
            reader = event_loop.create_task(anext(publisher.subscribe()))
            await asyncio.sleep(0)
            publisher.stop()
            with pytest.raises(StopAsyncIteration):
                await asyncio.wait_for(reader, timeout=1)

        event_loop.run_until_complete(check())


class TestStdinReady:
    def test_completed_future_does_not_set_result(
        self,
        event_loop: asyncio.AbstractEventLoop,
        stdin_pipe: Tuple[int, int],
    ) -> None:
        errors = []
        event_loop.set_exception_handler(
            lambda _loop, context: errors.append(context)
        )
        future = stdin_ready()
        future.set_result(None)
        os.write(stdin_pipe[1], b"x")
        event_loop.run_until_complete(asyncio.sleep(0.01))
        assert not event_loop.remove_reader(stdin_pipe[0])
        assert not errors

    def test_unregisters_on_cancellation(
        self,
        event_loop: asyncio.AbstractEventLoop,
        stdin_pipe: Tuple[int, int],
    ) -> None:
        future = stdin_ready()
        future.cancel()
        event_loop.run_until_complete(asyncio.sleep(0))
        assert not event_loop.remove_reader(stdin_pipe[0])

    def test_unregisters_on_readiness(
        self,
        event_loop: asyncio.AbstractEventLoop,
        stdin_pipe: Tuple[int, int],
    ) -> None:
        errors = []
        event_loop.set_exception_handler(
            lambda _loop, context: errors.append(context)
        )
        future = stdin_ready()
        os.write(stdin_pipe[1], b"x")
        assert event_loop.run_until_complete(future) is None
        event_loop.run_until_complete(asyncio.sleep(0))
        assert not event_loop.remove_reader(stdin_pipe[0])
        assert not errors


class TestLoopStdinReady:

    def test_async_for(
        self,
        event_loop: asyncio.AbstractEventLoop,
        stdin_pipe: Tuple[int, int],
    ) -> None:
        async def check() -> None:
            reader = loop_stdin_ready()
            notifications: list[None] = []
            os.write(stdin_pipe[1], b"a")
            try:
                async for notification in reader:
                    notifications.append(notification)
                    assert os.read(stdin_pipe[0], 1) == b"a"
                    assert not event_loop.remove_reader(stdin_pipe[0])
                    if len(notifications) == 2:
                        await reader.aclose()
                    else:
                        os.write(stdin_pipe[1], b"a")
            finally:
                await reader.aclose()
            assert notifications == [None, None]

        event_loop.run_until_complete(asyncio.wait_for(check(), timeout=1))

    def test_close_pending_read(
        self,
        event_loop: asyncio.AbstractEventLoop,
        stdin_pipe: Tuple[int, int],
    ) -> None:
        async def check() -> None:
            reader = loop_stdin_ready()
            pending = event_loop.create_task(anext(reader))
            await asyncio.sleep(0)
            await reader.aclose()
            with pytest.raises(asyncio.CancelledError):
                await pending
            assert not event_loop.remove_reader(stdin_pipe[0])

        event_loop.run_until_complete(check())

    def test_repeated_readiness_and_close(
        self,
        event_loop: asyncio.AbstractEventLoop,
        stdin_pipe: Tuple[int, int],
    ) -> None:
        async def check() -> None:
            reader = loop_stdin_ready()
            assert aiter(reader) is reader
            for _ in range(2):
                os.write(stdin_pipe[1], b"x")
                await anext(reader)
                assert os.read(stdin_pipe[0], 1) == b"x"
                assert not event_loop.remove_reader(stdin_pipe[0])
            await reader.aclose()
            with pytest.raises(StopAsyncIteration):
                await anext(reader)

        event_loop.run_until_complete(check())


class TestPython35Compatibility:
    def test_no_async_generators(self) -> None:
        source = Path("src/bonipy35/asyncio_ext.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source, feature_version=(3, 5))
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                assert not any(
                    isinstance(child, ast.Yield) for child in ast.walk(node)
                )


class TestRun:
    @pytest.fixture(autouse=True, params=[False, True])
    def fixture_runner(
        self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
    ) -> Iterator[None]:
        previous = asyncio.get_event_loop_policy()
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        try:
            if request.param:
                monkeypatch.delattr(asyncio, "run")
            yield
        finally:
            asyncio.set_event_loop_policy(previous)

    def test_python35_task_lookup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:

        # Exercise the legacy lookup
        # without modifying the immutable Task type.
        class LegacyTask:
            all_tasks = staticmethod(asyncio.all_tasks)

        monkeypatch.delattr(asyncio, "all_tasks")
        monkeypatch.setattr(asyncio, "Task", LegacyTask)

        async def app() -> int:
            return 7

        assert run(app()) == 7

    def test_return_and_loop_cleanup(self) -> None:
        loops = []

        async def app() -> int:
            loops.append(asyncio.get_event_loop())
            return 42

        assert run(app()) == 42
        assert run(app()) == 42
        assert loops[0] is not loops[1]
        assert all(loop.is_closed() for loop in loops)
        with pytest.raises(RuntimeError):
            asyncio.get_event_loop()

    def test_shutdown_error(self) -> None:
        errors = []

        async def background() -> None:
            try:
                await asyncio.sleep(100)
            finally:
                raise ValueError("shutdown")

        async def app() -> None:
            asyncio.get_event_loop().set_exception_handler(
                lambda _loop, context: errors.append(context)
            )
            asyncio.get_event_loop().create_task(background())
            await asyncio.sleep(0)

        run(app())
        assert str(errors[0]["exception"]) == "shutdown"

    def test_task_cleanup_and_failure(self) -> None:
        cleaned = []

        async def background() -> None:
            try:
                await asyncio.sleep(100)
            finally:
                cleaned.append(True)

        async def app() -> None:
            asyncio.get_event_loop().create_task(background())
            await asyncio.sleep(0)
            raise ValueError("application failed")

        with pytest.raises(ValueError, match="application failed"):
            run(app())
        assert cleaned == [True]
