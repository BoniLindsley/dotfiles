#!/usr/bin/env python3

# Standard libraries.
import argparse
import datetime
import logging
import math
import sys
import time
import tkinter
import tkinter.font
import typing

from typing import Dict, List, Union

# Internal libraries.
from .. import logging_ext
from ..logging_ext import TRACE
from .timer import Timer

_logger = logging.getLogger(__name__)


def get_font_height(
    size: int,
    *,
    size_to_height_cache: Dict[int, int],
    font: Union[None, tkinter.font.Font] = None
) -> int:
    height = size_to_height_cache.get(size)
    if height is not None:
        _logger.log(TRACE, "Font size %s has height %s.", size, height)
        return height
    if font is None:
        font = tkinter.font.Font(size=size)
    else:
        font.config(size=size)
    height = font.metrics()["linespace"]
    size_to_height_cache[size] = height
    _logger.log(TRACE, "Font size %s has height %s. (New.)", size, height)
    return height


def get_maximum_font_size(
    height: int,
    *,
    size_to_height_cache: Union[None, Dict[int, int]] = None,
    font: Union[None, tkinter.font.Font] = None
) -> int:
    if size_to_height_cache is None:
        size_to_height_cache = {}

    # Find an upper bound, then the largest size whose line height fits.
    minimum_size = 1
    maximum_size = 2
    while (
        get_font_height(
            maximum_size, size_to_height_cache=size_to_height_cache, font=font
        )
        <= height
    ):
        minimum_size = maximum_size
        maximum_size *= 2
    while maximum_size - minimum_size > 1:
        size = (minimum_size + maximum_size) // 2
        if (
            get_font_height(
                size, size_to_height_cache=size_to_height_cache, font=font
            )
            <= height
        ):
            minimum_size = size
        else:
            maximum_size = size
    return minimum_size


class ClockLabel(tkinter.Label):
    def __init__(
        self, *args: typing.Any, **kwargs: typing.Any
    ) -> None:  # pragma: no cover
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
        # Measure the actual family, style and text rather than a default font.
        new_font_size = get_maximum_font_size(
            max(1, height - 2 * int(self["pady"]) - 2),
            size_to_height_cache=font_size_to_height_cache,
            font=label_font,
        )
        available_width = max(1, width - 2 * int(self["padx"]) - 2)
        text = self["text"] or "00:00"
        minimum_size = 1
        maximum_size = new_font_size
        while minimum_size < maximum_size:
            size = (minimum_size + maximum_size + 1) // 2
            label_font.config(size=size)
            if label_font.measure(text) <= available_width:
                minimum_size = size
            else:
                maximum_size = size - 1
        label_font.config(size=minimum_size)
        self.config(font=label_font)

    def update_clock(self) -> None:
        _logger.log(TRACE, "Updating clock.")
        now = datetime.datetime.now()
        new_text = now.time().strftime("%H:%M")
        self.config(text=new_text)
        _logger.log(TRACE, "Updating clock to %s.", new_text)

        next_minute = now.replace(
            second=0, microsecond=0
        ) + datetime.timedelta(minutes=1)
        new_update = next_minute - now
        _logger.log(
            5,
            "Updating clock in %s seconds.",
            new_update // datetime.timedelta(seconds=1),
        )
        self.after(
            max(1, math.ceil(new_update.total_seconds() * 1000)),
            self.update_clock,
        )


class WrappingFrame(tkinter.Frame):
    def __init__(
        self, *args: typing.Any, **kwargs: typing.Any
    ) -> None:  # pragma: no cover
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


class TimerFrame(tkinter.Frame):
    def __init__(
        self,
        *args: typing.Any,
        duration: datetime.timedelta,
        **kwargs: typing.Any
    ) -> None:  # pragma: no cover
        super().__init__(*args, **kwargs)
        self.timer = Timer(duration=duration)
        self._after_id = None  # type: Union[None, str]
        self.bind("<Destroy>", self._on_destroy)

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

    def _cancel_step(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _on_destroy(self, event: tkinter.Event) -> None:
        if event.widget is self:
            self._cancel_step()

    def pause(self) -> None:
        self._cancel_step()
        self.timer.pause()
        self.update_display()

    def reset(self) -> None:
        self.timer.reset()
        self.step()

    def resume(self) -> None:
        now = time.monotonic()
        self.timer.resume(now=now)
        self.step(now=now)

    def step(self, *, now: Union[None, float] = None) -> None:
        self._cancel_step()
        timer = self.timer
        timer.update(now=now)
        self.update_display()

        if timer.is_active():
            # Wake when the rounded-up seconds display will next change.
            # An exact integer requires a full second, never a zero-delay loop.
            seconds = timer.remaining.total_seconds()
            fraction = seconds - math.ceil(seconds) + 1
            wait_time_ms = max(1, math.ceil(fraction * 1000))
            self._after_id = self.after(wait_time_ms, self.step)

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


def run() -> int:  # pragma: no cover
    root = tkinter.Tk()
    root.attributes("-topmost", "1")
    root.geometry("640x240")
    root.title(__package__ or "Floaty")

    wrapping_frame = WrappingFrame(root)
    wrapping_frame.pack(expand=True, fill=tkinter.BOTH)
    timer_frame = TimerFrame(root, duration=datetime.timedelta(seconds=30))
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
