#!/usr/bin/env python3

# Standard libraries.
import asyncio
import curses
import selectors
import signal
import threading
import time

from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext.asyncio_loop import (
    EventLoop,
    EventLoopPolicy,
    _Selector,
    run,
    use_event_loop_policy,
)


class TestSelector:
    def test_indefinite_wait(self, loop: EventLoop, window: Mock) -> None:
        window.getch.return_value = ord("a")
        assert _Selector(loop).select() == [
            (
                selectors.SelectorKey(
                    fileobj=0,
                    fd=0,
                    events=selectors.EVENT_READ,
                    data=ord("a"),
                ),
                selectors.EVENT_READ,
            )
        ]
        window.timeout.assert_called_with(-1)
        curses.doupdate.assert_not_called()  # type: ignore[attr-defined]
        window.refresh.assert_not_called()
        window.noutrefresh.assert_not_called()

    @pytest.mark.parametrize(
        "seconds, milliseconds",
        [(0, 0), (0.0001, 1), (0.0121, 13), (1e20, 2147483647)],
    )
    def test_deadline(
        self, loop: EventLoop, window: Mock, seconds: float, milliseconds: int
    ) -> None:
        assert not _Selector(loop).select(seconds)
        window.timeout.assert_called_with(milliseconds)


class TestEventLoop:
    def test_keys_fifo_and_timers(
        self, loop: EventLoop, window: Mock
    ) -> None:
        window.getch.side_effect = [-1, -1, ord("a"), curses.KEY_RESIZE] + [
            -1
        ] * 20

        async def check() -> None:
            first = loop.create_task(loop.getch())
            second = loop.create_task(loop.getch())
            assert await first == ord("a")
            assert await second == curses.KEY_RESIZE

        loop.run_until_complete(asyncio.wait_for(check(), 1))

    def test_cancel_preserves_key(
        self, loop: EventLoop, window: Mock
    ) -> None:
        async def check() -> None:
            task = loop.create_task(loop.getch())
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            window.getch.return_value = 42
            assert await loop.getch() == 42

        loop.run_until_complete(check())

    def test_buffered_keys(self, loop: EventLoop, window: Mock) -> None:
        window.getch.return_value = 12
        loop.run_until_complete(asyncio.sleep(0))
        assert loop.run_until_complete(loop.getch()) == 12

    def test_cancel_before_start(self, loop: EventLoop) -> None:
        task = loop.create_task(loop.getch())
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            loop.run_until_complete(task)

    def test_callback_after_completion(self, loop: EventLoop) -> None:
        future = loop.create_future()
        future.set_result(1)
        values = []
        future.add_done_callback(lambda done: values.append(done.result()))
        loop.run_until_complete(asyncio.sleep(0))
        assert values == [1]

    def test_thread_wakeup(
        self, loop: EventLoop, window: Mock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        loop.wakeup_signal = signal.SIGUSR2
        sent_signals = []
        # Simulate a blocking getch interrupted by the loop's wakeup signal.
        blocked = threading.Event()
        awakened = threading.Event()

        def getch() -> int:
            if window.timeout.call_args.args[0] != 0:
                blocked.set()
                assert awakened.wait(1)
            return -1

        window.getch.side_effect = getch

        def wake(thread_id: int, wakeup_signal: int) -> None:
            sent_signals.append((thread_id, wakeup_signal))
            awakened.set()

        monkeypatch.setattr(
            "bonipy35.curses_ext.asyncio_loop.signal.pthread_kill", wake
        )
        ready = loop.create_future()

        def worker() -> None:
            assert blocked.wait(1)
            loop.call_soon_threadsafe(ready.set_result, 42)

        thread = threading.Thread(target=worker)
        thread.start()
        try:
            assert loop.run_until_complete(ready) == 42
        finally:
            thread.join(timeout=2)
        assert not thread.is_alive()
        assert sent_signals == [
            (threading.main_thread().ident, signal.SIGUSR2)
        ]
        assert window.timeout.call_args_list[0].args == (-1,)

    def test_no_periodic_wakeups(self, loop: EventLoop, window: Mock) -> None:
        def getch() -> int:
            milliseconds = window.timeout.call_args.args[0]
            if milliseconds > 0:
                time.sleep(milliseconds / 1000)
            return -1

        window.getch.side_effect = getch
        loop.run_until_complete(asyncio.sleep(0.05))
        waits = [
            call.args[0]
            for call in window.timeout.call_args_list
            if call.args[0] > 0
        ]
        assert len(waits) == 1
        assert waits[0] >= 49

    def test_unsupported_readiness(self, loop: EventLoop) -> None:
        with pytest.raises(NotImplementedError):
            loop.add_reader(0, lambda: None)
        with pytest.raises(NotImplementedError):
            loop.add_writer(0, lambda: None)

    def test_wakeup_signal_restored(self, loop: EventLoop) -> None:
        loop.wakeup_signal = signal.SIGUSR2
        previous = signal.getsignal(loop.wakeup_signal)
        original_signal = signal.getsignal(signal.SIGUSR1)
        loop.run_until_complete(asyncio.sleep(0))
        assert signal.getsignal(loop.wakeup_signal) is previous
        assert signal.getsignal(signal.SIGUSR1) is original_signal
        loop.call_soon_threadsafe(lambda: None)  # No signal outside a run.

    def test_wakeup_key(self, loop: EventLoop, window: Mock) -> None:
        loop.wakeup_key = curses.KEY_MAX + 2
        # pylint: disable-next=protected-access
        loop._wake(loop.wakeup_signal, None)
        # pylint: disable-next=protected-access
        loop._wake(loop.wakeup_signal, None)
        curses.ungetch.assert_called_with(loop.wakeup_key)  # type: ignore[attr-defined]
        assert curses.ungetch.call_count == 2  # type: ignore[attr-defined]
        window.getch.return_value = curses.ungetch.call_args.args[0]  # type: ignore[attr-defined]
        assert not _Selector(loop).select(0)

    def test_full_pushback_queue(
        self, loop: EventLoop, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            curses, "ungetch", Mock(side_effect=curses.error())
        )
        loop._wake(signal.SIGUSR1, None)  # pylint: disable=protected-access

    def test_cancelled_waiter(self, loop: EventLoop) -> None:
        waiter = loop.create_future()
        waiter.cancel()
        loop._input_waiters.append(waiter)  # pylint: disable=protected-access
        loop._process_events(  # pylint: disable=protected-access
            [
                (
                    selectors.SelectorKey(
                        fileobj=0, fd=0, events=selectors.EVENT_READ, data=42
                    ),
                    selectors.EVENT_READ,
                )
            ]
        )
        assert loop.run_until_complete(loop.getch()) == 42

    def test_input_error(self, loop: EventLoop, window: Mock) -> None:
        window.getch.side_effect = curses.error("failed")
        with pytest.raises(curses.error):
            loop.run_until_complete(asyncio.sleep(0))
        window.getch.side_effect = None
        # Finish the task left pending when the wait mechanism failed.
        for task in asyncio.all_tasks(loop):
            loop.run_until_complete(task)

    def test_close(self, loop: EventLoop, window: Mock) -> None:
        waiter = loop.create_future()
        loop._input_waiters.append(waiter)  # pylint: disable=protected-access
        loop.close()
        loop.close()
        assert waiter.cancelled()
        window.timeout.assert_called_with(-1)
        with pytest.raises(RuntimeError, match="closed"):
            asyncio.run(loop.getch())

    def test_wrong_loop(self, loop: EventLoop) -> None:
        other = asyncio.new_event_loop()
        try:
            with pytest.raises(RuntimeError, match="owning"):
                other.run_until_complete(loop.getch())
        finally:
            other.close()

    def test_close_running(self, loop: EventLoop) -> None:
        async def check() -> None:
            with pytest.raises(RuntimeError, match="running"):
                loop.close()

        loop.run_until_complete(check())


class TestPolicy:
    @pytest.mark.parametrize("fail", [False, True])
    def test_restores(self, window: Mock, fail: bool) -> None:
        previous = asyncio.get_event_loop_policy()
        try:
            with use_event_loop_policy(window) as policy:
                assert isinstance(policy, EventLoopPolicy)
                assert asyncio.get_event_loop_policy() is policy
                if fail:
                    raise ValueError()
        except ValueError:
            pass
        assert asyncio.get_event_loop_policy() is previous


class TestRun:
    @pytest.fixture(autouse=True, params=[False, True])
    def fixture_runner(
        self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if request.param:
            monkeypatch.delattr(asyncio, "run")

    def test_repeated_run(self, window: Mock) -> None:
        async def app() -> int:
            loop = asyncio.get_event_loop()
            assert isinstance(loop, EventLoop)
            assert loop.window is window
            return 42

        assert run(app()) == 42
        assert run(app()) == 42

    def test_terminal_cleanup_on_failure(self, window: Mock) -> None:
        async def app() -> None:
            raise ValueError("application failed")

        with pytest.raises(ValueError, match="application failed"):
            run(app())
        window.keypad.assert_called_with(False)
        curses.echo.assert_called_once()  # type: ignore[attr-defined]
        curses.nocbreak.assert_called_once()  # type: ignore[attr-defined]
        curses.endwin.assert_called_once()  # type: ignore[attr-defined]
