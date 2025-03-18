#!/usr/bin/env python3

# This is work in progress. Leaving in TODO as progress reminder.
# pylint: disable=fixme

# TODO: Summarise total time by topic.
# TODO: Summarise total time by time range.

# Standard libraries.
import collections
import datetime
import logging
import typing

# Internal modules.
import bonipy.taskmd
import vim


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


def end_clock() -> None:
    # TODO: Close the first unclosed clock.
    pass


def start_clock() -> None:
    last_title = None  # type: None | bonipy.taskmd.Title
    cursor_row = vim.current.window.cursor[0]

    heading_parser = bonipy.taskmd.HeadingParser()
    last_heading = None  # type: None | bonipy.taskmd.Clock | bonipy.taskmd.Title
    for line in vim.current.buffer[: cursor_row + 1]:
        heading_parser.send_line(line)
        if not heading_parser.headings:
            continue
        if heading_parser.headings[-1] is last_heading:
            continue
        last_heading = heading_parser.headings[-1]
        if "headline" in last_heading:
            last_title = typing.cast(bonipy.taskmd.Title, last_heading)

    new_line_number = 1
    new_clock_level = 1
    if last_title:
        new_line_number = last_title["line_number"]
        new_clock_level = last_title["level"] + 1
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    new_start_time = now.strftime("%Y-%m-%dT%H:%M:%S%z")
    vim.current.buffer.append(
        [
            "",
            "#" * new_clock_level + " CLOCK: [" + new_start_time + "]",
            "",
            str(heading_parser.headings),
            str(last_heading),
            str(last_title),
            str(new_line_number),
        ],
        new_line_number,
    )


def write_timesheet_to_qlist() -> None:
    # TODO: Order day by time.
    pass


def fix_clocks() -> None:
    # TODO: Rewrite all duration suffix for clocks.
    # TODO: Rewrite all clocks to "standard" format.
    pass


def write_summary_to_qlist() -> None:
    heading_parser = bonipy.taskmd.HeadingParser()
    bufnr = vim.current.buffer.number
    for line in vim.current.buffer[:]:
        heading_parser.send_line(line)

    title_durations = bonipy.taskmd.get_title_durations(heading_parser.headings)
    summed_durations = bonipy.taskmd.sum_durations(title_durations)
    summed_durations = collections.deque(
        filter(
            lambda title_total_duration: title_total_duration["total_duration"],
            summed_durations,
        )
    )
    hour = datetime.timedelta(hours=1)

    new_list = []
    line = "Duration / h | Headline"
    new_list.append({"bufnr": bufnr, "lnum": 1, "col": 1, "text": line})
    for title_total_duration in summed_durations:
        if title_total_duration["total_duration"]:
            level = title_total_duration["level"]
            headline = title_total_duration["headline"] or ""
            if level:
                headline = "  " * (level - 1) + "* " + headline
            else:
                headline = f"Total: {headline}" if headline else "Total"

            line = (
                f"{title_total_duration['total_duration'] / hour:>12.2f} | {headline}"
            )
            new_list.append(
                {
                    "bufnr": bufnr,
                    "lnum": title_total_duration["line_number"],
                    "col": 1,
                    "text": line,
                }
            )

    vim.eval(f"setqflist({new_list})")
