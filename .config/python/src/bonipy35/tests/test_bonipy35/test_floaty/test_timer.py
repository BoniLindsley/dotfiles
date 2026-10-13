#!/usr/bin/env python3

import datetime
from unittest.mock import patch

import pytest

from bonipy35.floaty.timer import Timer


@pytest.fixture(name="timer")
def fixture_timer() -> Timer:
    return Timer(duration=datetime.timedelta(seconds=30))


class TestUpdate:
    def test_paused_timer_does_not_change(self, timer: Timer) -> None:
        timer.update(now=100)
        assert timer.remaining.total_seconds() == 30

    def test_elapsed_time_and_expiry(self, timer: Timer) -> None:
        timer.resume(now=0)
        timer.update(now=10)
        assert timer.remaining.total_seconds() == 20
        assert timer.is_active()
        timer.update(now=50)
        assert timer.remaining == datetime.timedelta()
        assert not timer.is_active()

    def test_uses_monotonic_clock(self, timer: Timer) -> None:
        with patch(
            "bonipy35.floaty.timer.time.monotonic", side_effect=[100, 110]
        ):
            timer.resume()
            timer.update()
        assert timer.remaining.total_seconds() == 20


class TestReset:
    def test_running_reset_starts_full_duration_at_reset(
        self, timer: Timer
    ) -> None:
        timer.resume(now=0)
        timer.reset(now=10)
        timer.update(now=11)
        assert timer.remaining.total_seconds() == 29
        assert timer.is_active()

    def test_paused_reset_stays_paused(self, timer: Timer) -> None:
        timer.remaining = datetime.timedelta(seconds=2)
        with patch("bonipy35.floaty.timer.time.monotonic", return_value=10):
            timer.reset()
        assert timer.remaining.total_seconds() == 30
        assert not timer.is_active()


class TestResume:
    def test_resume_is_idempotent(self, timer: Timer) -> None:
        timer.resume(now=0)
        timer.resume(now=10)
        timer.update(now=11)
        assert timer.remaining.total_seconds() == 19

    def test_pause_and_resume_freeze_remaining(self, timer: Timer) -> None:
        timer.resume(now=0)
        with patch("bonipy35.floaty.timer.time.monotonic", return_value=10):
            timer.pause()
        assert timer.remaining.total_seconds() == 20
        timer.resume(now=100)
        timer.update(now=101)
        assert timer.remaining.total_seconds() == 19
