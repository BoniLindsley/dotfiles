#!/usr/bin/env python3

# Standard libraries.
import datetime
import time
import typing

from typing import Union


class Timer:
    """Local countdown; optional ``now`` values are monotonic seconds.

    Monotonic elapsed time avoids changing the countdown on wall-clock edits.
    """

    def __init__(
        self,
        *args: typing.Any,
        duration: datetime.timedelta,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.duration = duration
        self.last_active_update_time = None  # type: Union[None, float]
        self.remaining = self.duration

    def is_active(self) -> bool:
        return self.last_active_update_time is not None

    def pause(self) -> None:
        self.update()
        self.last_active_update_time = None

    def reset(self, *, now: Union[None, float] = None) -> None:
        if now is None:
            now = time.monotonic()

        self.remaining = self.duration
        if self.is_active():
            self.last_active_update_time = now

    def resume(self, *, now: Union[None, float] = None) -> None:
        if now is None:
            now = time.monotonic()

        if not self.is_active():
            self.last_active_update_time = now

    def update(self, *, now: Union[None, float] = None) -> None:
        last_active_update_time = self.last_active_update_time
        if last_active_update_time is None:
            return

        if now is None:
            now = time.monotonic()

        step_duration = datetime.timedelta(
            seconds=max(0.0, now - last_active_update_time)
        )
        zero_duration = datetime.timedelta()
        self.remaining = max(self.remaining - step_duration, zero_duration)

        if self.remaining > zero_duration:
            self.last_active_update_time = now
        else:
            self.last_active_update_time = None
