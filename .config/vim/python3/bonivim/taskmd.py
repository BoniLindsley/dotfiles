#!/usr/bin/env python3

# This is work in progress. Leaving in TODO as progress reminder.
# pylint: disable=fixme

# TODO: Summarise total time by topic.
# TODO: Summarise total time by time range.

# Standard libraries.
import argparse
import collections
import contextlib
import datetime
import logging
import re
import sys
import typing

from typing import Generator


_logger = logging.getLogger(__name__)
LOGGING_ALL = 1
LOGGING_TRACE = 5


def set_up_logging(*, logger: logging.Logger) -> None:
    logging.addLevelName(LOGGING_ALL, "ALL")
    logging.addLevelName(LOGGING_TRACE, "TRACE")

    formatter = logging.Formatter(
        datefmt="%Y-%m-%d %H:%M:%S",
        fmt="[{asctime}] [python/{name}] [{levelname[0]}] {message}",
        style="{",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def set_logger_verbosity(
    *, logger: logging.Logger, verbosity: typing.Union[None | int] = None
) -> None:
    if verbosity is None:
        verbosity = 0

    verbosity_map = {
        -2: logging.CRITICAL,
        -1: logging.ERROR,
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: LOGGING_TRACE,
        4: LOGGING_ALL,
    }
    minimum_verbosity = min(verbosity_map)
    maximum_verbosity = max(verbosity_map)
    verbosity = min(maximum_verbosity, verbosity)
    verbosity = max(minimum_verbosity, verbosity)
    logging_level = verbosity_map.get(verbosity, logging.WARNING)
    logger.setLevel(logging_level)


def add_verbose_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        dest="verbosity",
        help="Incrase verbosity.",
    )


def read_lines(
    *, buffer_size: None | int = None, source: typing.TextIO
) -> Generator[str, None, None]:

    default_buffer_size = 4096

    if buffer_size is None:
        buffer_size = default_buffer_size
    if buffer_size <= 0:
        return

    while True:
        line = source.readline(buffer_size)
        # Empty line if at EOF.
        if not line:
            return
        if len(line) >= buffer_size:
            raise BufferError(f"Line too long to fit in buffer of size {buffer_size}")
        # Line always has a trailing new line unless ending in EOF.
        # Check line ending of source. Strip line ending before yielding line.
        line = line.removesuffix(source.newlines or "\n")
        yield line


@contextlib.contextmanager
def suppress_keyboard_interrupt() -> Generator[None, None, None]:
    try:
        yield
    except KeyboardInterrupt:
        # Clear line echo-ing "^C".
        print()


to_clock_regex = re.compile(
    "(?P<level>#+)"
    "( +)CLOCK:( +)"
    r"\[(?P<start>[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+[+-][0-9]+:[0-9]+)\]"
    "--"
    r"\[(?P<end>[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+[+-][0-9]+:[0-9]+)\]"
)


class Clock(typing.TypedDict):
    level: int
    start: datetime.datetime
    end: datetime.datetime


def to_clock(line: str) -> None | Clock:
    match = to_clock_regex.match(line)
    if not match:
        return None
    return {
        "level": len(match["level"]),
        "start": datetime.datetime.fromisoformat(match["start"]),
        "end": datetime.datetime.fromisoformat(match["end"]),
    }


to_title_regex = re.compile(
    "(?P<level>#+)"
    "(( +)((?P<state>DONE|TODO)))?"
    r"(( +)(\[#(?P<priority>.)\]))?"
    "( +)(?P<headline>.*?)"
    "(( +)(?P<tags>(:[0-9:@A-Z_a-z]+:)?))?$"
)


class Title(typing.TypedDict):
    level: int
    state: None | str
    priority: None | str
    headline: None | str
    tags: None | str


def to_title(line: str) -> None | Title:
    match = to_title_regex.match(line)
    if not match:
        return None
    return {
        "level": len(match["level"]),
        "state": match["state"],
        "priority": match["priority"],
        "headline": match["headline"],
        "tags": match["tags"],
    }


def to_headings(stdin: typing.TextIO) -> list[Clock | Title]:
    headings = []  # type: list[Clock | Title]
    inside_code_block = False
    for line in read_lines(source=stdin):
        if inside_code_block:
            if line == "```":
                inside_code_block = False
        elif line.startswith("```"):
            inside_code_block = True
        elif clock := to_clock(line):
            headings.append(clock)
        elif title := to_title(line):
            headings.append(title)
    return headings


class TitleDuration(Title):
    duration: datetime.timedelta


def get_title_durations(headings: list[Clock | Title]) -> list[TitleDuration]:
    last_title_duration = {
        "level": 0,
        "state": None,
        "priority": None,
        "headline": "",
        "tags": None,
        "duration": datetime.timedelta(),
    }  # type: TitleDuration
    title_durations = [last_title_duration]
    for heading in headings:
        try:
            start = heading["start"]  # type: ignore[typeddict-item]
            end = heading["end"]  # type: ignore[typeddict-item]
        except KeyError:
            title = heading  # type: Title  # type: ignore[assignment]
            last_title_duration = {
                **title,
                "duration": datetime.timedelta(),
            }
            title_durations.append(last_title_duration)
        else:
            duration = end - start
            last_title_duration["duration"] += duration
    return title_durations


class TitleTotalDuration(TitleDuration):
    total_duration: datetime.timedelta


def sum_durations(
    title_durations: list[TitleDuration],
) -> collections.deque[TitleTotalDuration]:
    summed_durations = (
        collections.deque()
    )  # type: collections.deque[TitleTotalDuration]
    # Level zero is root.
    child_level_durations = [datetime.timedelta()]
    for title_duration in reversed(title_durations):
        level = title_duration["level"]
        total_duration = sum(
            child_level_durations[level + 1 :], start=title_duration["duration"]
        )
        summed_durations.appendleft(
            {
                **title_duration,
                "total_duration": total_duration,
            }
        )

        missing_levels = level + 1 - len(child_level_durations)
        if missing_levels > 0:
            child_level_durations += [datetime.timedelta()] * missing_levels
        else:
            child_level_durations = child_level_durations[: level + 1]
        child_level_durations[level] += total_duration
    return summed_durations


def run(stdin: typing.TextIO, stdout: typing.TextIO) -> int:
    headings = to_headings(stdin)
    title_durations = get_title_durations(headings)
    summed_durations = sum_durations(title_durations)
    summed_durations = collections.deque(
        filter(
            lambda title_total_duration: title_total_duration["total_duration"],
            summed_durations,
        )
    )
    hour = datetime.timedelta(hours=1)
    print("Duration / h | Headline", file=stdout)
    for title_total_duration in summed_durations:
        if title_total_duration["total_duration"]:
            level = title_total_duration["level"]
            headline = title_total_duration["headline"] or ""
            if level:
                headline = "  " * (level - 1) + "* " + headline
            else:
                headline = f"Total: {headline}" if headline else "Total"
            print(
                f"{title_total_duration['total_duration'] / hour:>12.2f} | {headline}",
                file=stdout,
            )
    return 0


def parse_arguments(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_verbose_flag(parser)
    return parser.parse_args(args)


@suppress_keyboard_interrupt()
def main(argv: None | list[str] = None) -> int:
    if argv is None:
        argv = sys.argv

    set_up_logging(logger=_logger)

    arguments = parse_arguments(argv[1:])
    set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    return run(stdin=sys.stdin, stdout=sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
