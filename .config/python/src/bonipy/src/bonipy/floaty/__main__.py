#!/usr/bin/env python3

# Standard libraries.
import argparse
import datetime
import logging
import sys
import tkinter
import tkinter.font
import typing

from typing import Dict, List, Union


_logger = logging.getLogger(__name__)
TRACE = 5


def set_logger_verbosity(
    *, logger: logging.Logger, verbosity: int
) -> None:
    logging.addLevelName(1, "ALL")
    logging.addLevelName(TRACE, "TRACE")
    verbosity_map = {
        -2: logging.CRITICAL,
        -1: logging.ERROR,
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: TRACE,
    }
    minimum_verbosity = min(verbosity_map)
    maximum_verbosity = max(verbosity_map)
    verbosity = int(verbosity)
    verbosity = min(maximum_verbosity, verbosity)
    verbosity = max(minimum_verbosity, verbosity)
    logging_level = verbosity_map.get(verbosity, logging.WARNING)
    logger.setLevel(logging_level)


def set_up_logging(
    *, logger: logging.Logger, verbosity: Union[None, int] = None
) -> None:
    formatter = logging.Formatter(
        datefmt="%Y-%m-%d %H:%M:%S",
        fmt="[{asctime}] [python/{name}] [{levelname[0]}] {message}",
        style="{",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if verbosity is not None:
        set_logger_verbosity(logger=logger, verbosity=verbosity)


def parse_arguments(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        dest="verbosity",
        help="Incrase verbosity.",
    )
    return parser.parse_args(args)


def get_font_height(
    size: int, *, size_to_height_cache: Dict[int, int]
) -> int:
    height = size_to_height_cache.get(size)
    if height is not None:
        _logger.log(TRACE, "Font size %s has height %s.", size, height)
        return height
    height = tkinter.font.Font(size=size).metrics()["linespace"]
    size_to_height_cache[size] = height
    _logger.log(
        TRACE, "Font size %s has height %s. (New.)", size, height
    )
    return height


def get_maximum_font_size(
    height: int,
    *,
    size_to_height_cache: Union[None, Dict[int, int]] = None
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
            TRACE,
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

    def update_clock(self) -> None:
        _logger.log(TRACE, "Updating clock.")
        now = datetime.datetime.now()
        new_text = now.time().isoformat(timespec="minutes")
        self.config(text=new_text)
        _logger.log(TRACE, "Updating clock to %s.", new_text)

        next_minute = now.replace(second=0) + datetime.timedelta(
            minutes=1
        )
        new_update = next_minute - now
        _logger.log(
            TRACE,
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

        self.font_size_to_height_cache = {1: 2}
        self.font_size_to_height_cache.clear()

        self.bind("<Configure>", self.on_configure)

    def on_configure(self, event: tkinter.Event) -> None:  # type: ignore[type-arg]
        del event
        self.resize()

    def resize(self) -> None:
        # Try to ensure the whole label fits inside the frame.
        label = self.clock_label
        label_font = tkinter.font.Font(font=label["font"])
        old_font_size = label_font["size"]
        old_height = get_font_height(
            old_font_size,
            size_to_height_cache=self.font_size_to_height_cache,
        )
        old_width = tkinter.font.Font(size=old_font_size).measure(
            "00:00"
        )
        _logger.log(
            TRACE,
            "Resizing frame. Clock size was: %s x %s.",
            old_width,
            old_height,
        )

        max_height = old_height * self.winfo_width() // old_width
        new_height = max(1, min(max_height, self.winfo_height()))
        if not new_height - 8 < old_height < new_height:
            new_font_size = get_maximum_font_size(
                new_height,
                size_to_height_cache=self.font_size_to_height_cache,
            )
            label_font.config(size=new_font_size)
            label.config(font=label_font)
            _logger.log(
                TRACE,
                "Resizing clock to font size %s for height %s.",
                new_font_size,
                self.font_size_to_height_cache[new_font_size],
            )


def main(argv: Union[None, List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv

    arguments = parse_arguments(argv[1:])
    set_up_logging(logger=_logger, verbosity=arguments.verbosity)

    root = tkinter.Tk()
    root.attributes("-topmost", "1")
    root.geometry("640x240")
    root.title(__package__ or "Floaty")

    wrapping_frame = WrappingFrame(root)
    wrapping_frame.pack(expand=True, fill=tkinter.BOTH)

    _logger.log(TRACE, "Starting tkinter main loop.")
    root.tk.mainloop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
