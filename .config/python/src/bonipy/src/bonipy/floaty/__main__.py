#!/usr/bin/env python3

# Standard libraries.
import argparse
import datetime
import logging
import sys
import tkinter
import tkinter.font
import typing as t


_logger = logging.getLogger(__name__)
TRACE = 5


def initialise_logging(*, verbosity: int) -> None:
    logging.basicConfig()
    logging.addLevelName(TRACE, "TRACE")

    if verbosity > 0:
        if verbosity == 1:
            _logger.setLevel(logging.INFO)
        elif verbosity == 2:
            _logger.setLevel(logging.DEBUG)
        else:
            _logger.setLevel(TRACE)


def get_font_height(size: int, *, size_to_height_cache: dict[int, int]) -> int:
    height = size_to_height_cache.get(size)
    if height is not None:
        _logger.log(TRACE, "Font size %s has height %s.", size, height)
        return height
    height = tkinter.font.Font(size=size).metrics()["linespace"]
    size_to_height_cache[size] = height
    _logger.log(TRACE, "Font size %s has height %s. (New.)", size, height)
    return height


def get_maximum_font_size(
    height: int, *, size_to_height_cache: None | dict[int, int] = None
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
    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.after_idle(self.update_clock)

    def update_clock(self) -> None:
        _logger.log(TRACE, "Updating clock.")
        now = datetime.datetime.now()
        new_text = now.time().isoformat(timespec="minutes")
        self.config(text=new_text)
        _logger.log(TRACE, "Updating clock to %s.", new_text)

        next_minute = now.replace(second=0) + datetime.timedelta(minutes=1)
        new_update = next_minute - now
        _logger.log(
            TRACE,
            "Updating clock in %s seconds.",
            new_update // datetime.timedelta(seconds=1),
        )
        self.after(new_update // datetime.timedelta(milliseconds=1), self.update_clock)


class WrappingFrame(tkinter.Frame):
    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        clock_label = self.clock_label = ClockLabel(self)
        clock_label.pack(expand=True)

        self.font_size_to_height_cache: dict[int, int] = {}

        self.bind("<Configure>", self.on_configure)

    def on_configure(self, event: tkinter.Event) -> None:  # type: ignore[type-arg]
        del event
        self.resize()

    def resize(self) -> None:
        # Try to ensure the whole label fits inside the frame.
        label = self.clock_label
        old_font = label["font"]
        old_font_size = tkinter.font.Font(font=old_font)["size"]
        old_height = get_font_height(
            old_font_size, size_to_height_cache=self.font_size_to_height_cache
        )
        old_width = tkinter.font.Font(size=old_font_size).measure("00:00")
        _logger.log(
            TRACE, "Resizing frame. Clock size was: %s x %s.", old_width, old_height
        )

        max_height = old_height * self.winfo_width() // old_width
        new_height = max(1, min(max_height, self.winfo_height()))
        if not new_height - 8 < old_height < new_height:
            new_font_size = get_maximum_font_size(
                new_height, size_to_height_cache=self.font_size_to_height_cache
            )
            label.config(font=(None, new_font_size))
            _logger.log(
                TRACE,
                "Resizing clock to font size %s for height %s.",
                new_font_size,
                self.font_size_to_height_cache[new_font_size],
            )


class Application(tkinter.Tk):
    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.title(__package__)
        self.wrapping_frame = WrappingFrame(self)
        self.wrapping_frame.pack(expand=True, fill=tkinter.BOTH)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="count", default=0)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    initialise_logging(verbosity=arguments.verbose)

    application = Application()
    application.geometry("640x240")

    _logger.log(TRACE, "Starting tkinter main loop.")
    application.mainloop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
