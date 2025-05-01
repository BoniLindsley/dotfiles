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
    headline_parser = bonipy.taskmd.HeadlineParser()

    last_level = 0

    for line in vim.current.buffer:
        result = headline_parser.send(line)
        if not result:
            continue

        line_number, headline_entries = result

        if "level" in headline_entries:
            headline = typing.cast(bonipy.taskmd.Headline, headline_entries)
            last_level = headline["level"]

        if "start" not in headline_entries:
            continue

        clock = typing.cast(bonipy.taskmd.Clock, headline_entries)
        if "end" in clock:
            continue

        clock["end"] = (
            datetime.datetime.now(datetime.timezone.utc)
            .astimezone()
            .replace(microsecond=0)
        )

        new_clock_line = bonipy.taskmd.to_string_from_clock(clock)
        vim.current.buffer[line_number - 1] = (
            "#" * (last_level + 1) + " " + new_clock_line
        )

        break
    else:
        print("No clock has been started.")


def start_clock() -> None:
    cursor_row = vim.current.window.cursor[0]
    headlines = bonipy.taskmd.HeadlineParser.parse_all(
        stdin=vim.current.buffer[: cursor_row + 1]
    )
    for new_line_number, last_headline in reversed(headlines.items()):
        if "title" in last_headline:
            last_title = typing.cast(bonipy.taskmd.Headline, last_headline)
            new_clock_level = last_title["level"] + 1
            break
    else:
        new_clock_level = 1
        new_line_number = cursor_row

    clock = {
        "start": datetime.datetime.now(datetime.timezone.utc)
        .astimezone()
        .replace(microsecond=0)
    }  # type: bonipy.taskmd.Clock
    clock_line = bonipy.taskmd.to_string_from_clock(clock)
    vim.current.buffer.append(
        ["#" * new_clock_level + " " + clock_line],
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
    bufnr = vim.current.buffer.number
    headlines = bonipy.taskmd.HeadlineParser.parse_all(stdin=vim.current.buffer[:])

    headline_durations = bonipy.taskmd.get_headline_durations(headlines)
    summed_durations = bonipy.taskmd.sum_durations(headline_durations)
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
            headline = title_total_duration.get("title") or ""
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
