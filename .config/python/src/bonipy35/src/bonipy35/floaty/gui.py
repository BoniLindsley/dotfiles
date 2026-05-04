#!/usr/bin/env python3

# Python 3.5 does not have f-strings.
# pylint: disable=consider-using-f-string

# Standard libraries.
import argparse
import datetime
import logging
import math
import sys
import tkinter
import tkinter.font
import typing

from typing import Dict, List, Union

# Internal libraries.
from .. import logging_ext
from ..logging_ext import TRACE

_logger = logging.getLogger(__name__)


def get_font_height(
    size: int, *, size_to_height_cache: Dict[int, int]
) -> int:
    height = size_to_height_cache.get(size)
    if height is not None:
        _logger.log(TRACE, "Font size %s has height %s.", size, height)
        return height
    height = tkinter.font.Font(size=size).metrics()["linespace"]
    size_to_height_cache[size] = height
    _logger.log(TRACE, "Font size %s has height %s. (New.)", size, height)
    return height


def get_maximum_font_size(
    height: int, *, size_to_height_cache: Union[None, Dict[int, int]] = None
) -> int:
    if size_to_height_cache is None:
        size_to_height_cache = {}

    # Determine font sizes that bound given height.
    minimum_size = 1
    while True:
        maximum_size = minimum_size * 2
        if height <= get_font_height(
            maximum_size, size_to_height_cache=size_to_height_cache
        ):
            break
        minimum_size = maximum_size

    minimum_height = get_font_height(
        minimum_size, size_to_height_cache=size_to_height_cache
    )
    maximum_height = get_font_height(
        maximum_size, size_to_height_cache=size_to_height_cache
    )

    # Keep finding mid-point to find size for height.
    last_range = maximum_size - minimum_size
    while True:
        _logger.log(
            5,
            "Checking font size range %s to %s. Height: %s to %s.",
            minimum_size,
            maximum_size,
            minimum_height,
            maximum_height,
        )
        # Edge case that somehow becomes out of bound.
        if height <= minimum_height:
            return minimum_size
        if height >= maximum_height:
            return maximum_size

        # Determine mid-point.
        new_size = (minimum_size + maximum_size) // 2
        new_height = get_font_height(
            new_size, size_to_height_cache=size_to_height_cache
        )

        if new_height == height:
            return new_size
        if new_height < height:
            minimum_size = new_size
            minimum_height = new_height
        elif new_height > height:
            maximum_size = new_size
            maximum_height = new_height

        # Sanity check for forward progress.
        new_range = maximum_size - minimum_size
        if not 0 < new_range < last_range:
            break
        last_range = new_range

    return minimum_size


class ClockLabel(tkinter.Label):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.after_idle(self.update_clock)

    def resize(
        self,
        *,
        font_size_to_height_cache: Dict[int, int],
        height: int,
        width: int
    ) -> None:
        # Try to ensure the whole label fits inside the frame.
        label_font = tkinter.font.Font(font=self["font"])
        old_font_size = label_font["size"]
        old_height = get_font_height(
            old_font_size,
            size_to_height_cache=font_size_to_height_cache,
        )
        old_width = tkinter.font.Font(size=old_font_size).measure("00:00")
        _logger.log(
            5,
            "Resizing frame. Clock size was: %s x %s.",
            old_width,
            old_height,
        )

        # Do not change font if the current height is close enough.
        max_height = old_height * width // old_width
        new_height = max(1, min(max_height, height))
        resize_threshold = 8
        if new_height - resize_threshold < old_height < new_height:
            return

        new_font_size = get_maximum_font_size(
            new_height,
            size_to_height_cache=font_size_to_height_cache,
        )
        label_font.config(size=new_font_size)
        self.config(font=label_font)
        _logger.log(
            5,
            "Resizing clock to font size %s for height %s.",
            new_font_size,
            font_size_to_height_cache[new_font_size],
        )

    def update_clock(self) -> None:
        _logger.log(TRACE, "Updating clock.")
        now = datetime.datetime.now()
        new_text = now.time().strftime("%H:%M")
        self.config(text=new_text)
        _logger.log(TRACE, "Updating clock to %s.", new_text)

        next_minute = now.replace(second=0) + datetime.timedelta(minutes=1)
        new_update = next_minute - now
        _logger.log(
            5,
            "Updating clock in %s seconds.",
            new_update // datetime.timedelta(seconds=1),
        )
        self.after(
            new_update // datetime.timedelta(milliseconds=1),
            self.update_clock,
        )


class WrappingFrame(tkinter.Frame):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        clock_label = self.clock_label = ClockLabel(self)
        clock_label.pack(expand=True)

        self.font_size_to_height_cache = {}  # type: Dict[int, int]

        self.bind("<Configure>", self.on_configure)

    def on_configure(self, event: tkinter.Event) -> None:
        del event
        self.resize()

    def resize(self) -> None:
        # Try to ensure the whole label fits inside the frame.
        label = self.clock_label
        width = self.winfo_width()
        height = self.winfo_height()
        font_size_to_height_cache = self.font_size_to_height_cache
        label.resize(
            font_size_to_height_cache=font_size_to_height_cache,
            height=height,
            width=width,
        )


class Timer:
    def __init__(
        self,
        *args: typing.Any,
        duration: datetime.timedelta,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.duration = duration
        self.last_active_update_time = (
            None
        )  # type: Union[None, datetime.datetime]
        self.remaining = self.duration

    def is_active(self) -> bool:
        return self.last_active_update_time is not None

    def pause(self) -> None:
        self.update()
        self.last_active_update_time = None

    def reset(self, *, now: Union[None, datetime.datetime] = None) -> None:
        if now is None:
            now = datetime.datetime.now()

        self.remaining = self.duration

    def resume(self, *, now: Union[None, datetime.datetime] = None) -> None:
        if now is None:
            now = datetime.datetime.now()

        self.last_active_update_time = now
        self.update(now=now)

    def update(self, *, now: Union[None, datetime.datetime] = None) -> None:
        last_active_update_time = self.last_active_update_time
        if last_active_update_time is None:
            return

        if now is None:
            now = datetime.datetime.now()

        step_duration = now - last_active_update_time
        zero_duration = datetime.timedelta()
        self.remaining = max(self.remaining - step_duration, zero_duration)

        if self.remaining > zero_duration:
            self.last_active_update_time = now
        else:
            self.last_active_update_time = None


class TimerFrame(tkinter.Frame):
    def __init__(
        self,
        *args: typing.Any,
        duration: datetime.timedelta,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.timer = Timer(duration=duration)

        # display label
        self.time_label = tkinter.Label(self, font=("Helvetica", 24))
        self.time_label.pack(pady=10)

        # control buttons
        btn_frame = tkinter.Frame(self)
        btn_frame.pack()

        self.pause_btn = tkinter.Button(
            btn_frame, text="Resume", command=self.toggle_pause
        )
        self.pause_btn.grid(row=0, column=1, padx=2)

        self.reset_btn = tkinter.Button(
            btn_frame, text="Reset", command=self.reset
        )
        self.reset_btn.grid(row=0, column=2, padx=2)

        self.after_idle(self.update_display)

    def pause(self) -> None:
        self.timer.pause()
        self.update_display()

    def reset(self) -> None:
        self.timer.reset()
        self.update_display()

    def resume(self) -> None:
        now = datetime.datetime.now()
        self.timer.resume(now=now)
        self.step(now=now, repeat=True)

    def step(
        self,
        *,
        now: Union[None, datetime.datetime] = None,
        repeat: Union[None, bool] = None
    ) -> None:
        timer = self.timer
        timer.update(now=now)
        self.update_display()

        if repeat is None:
            repeat = timer.is_active()

        if repeat:
            wait_seconds = timer.remaining % datetime.timedelta(seconds=1)
            wait_time_ms = int(wait_seconds.total_seconds() * 1000)
            self.after(wait_time_ms, self.step)

    def toggle_pause(self) -> None:
        if self.timer.is_active():
            self.pause()
        else:
            self.resume()

    def update_display(self) -> None:
        timer = self.timer
        seconds = math.ceil(timer.remaining.total_seconds())
        text = "{:02d}".format(seconds)
        self.time_label.config(text=text)

        if timer.is_active():
            self.pause_btn.config(text="Pause")
        else:
            self.pause_btn.config(text="Resume")


def run() -> int:
    root = tkinter.Tk()
    root.attributes("-topmost", "1")
    root.geometry("640x240")
    root.title(__package__ or "Floaty")

    wrapping_frame = WrappingFrame(root)
    wrapping_frame.pack(expand=True, fill=tkinter.BOTH)
    timer_frame = TimerFrame(duration=datetime.timedelta(seconds=30))
    timer_frame.pack(expand=True, fill=tkinter.BOTH)

    _logger.log(TRACE, "Starting tkinter main loop.")
    root.tk.mainloop()

    return 0


def main(argv: Union[None, List[str]] = None) -> int:
    """Parse command line arguments and call `run`."""

    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    argument_parser = argparse.ArgumentParser()
    logging_ext.add_verbose_flag(argument_parser)
    arguments = argument_parser.parse_args(argv[1:])

    logging_ext.set_logger_verbosity(
        logger=_logger, verbosity=arguments.verbosity
    )

    return run()


if __name__ == "__main__":
    sys.exit(main())
