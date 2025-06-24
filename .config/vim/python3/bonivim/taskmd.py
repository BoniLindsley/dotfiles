#!/usr/bin/env python3

# This is work in progress. Leaving in TODO as progress reminder.
# pylint: disable=fixme

# TODO: Summarise total time by topic.
# TODO: Summarise total time by time range.

# ========
# Common code
# ========

# Standard libraries.
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


# ========
# Actual implementation
# ========


def end_clock() -> None:
    buffer = vim.current.buffer
    parsed_lines = bonipy.taskmd.to_parsed_lines(buffer)
    new_parsed_line = bonipy.taskmd.end_first_clock(
        parsed_lines, now=bonipy.taskmd.get_now()
    )
    if not new_parsed_line:
        print("No clock has been started.")
        return

    new_line_number = new_parsed_line["line_number"]
    new_content = bonipy.taskmd.to_string_from_parsed_line(new_parsed_line)
    buffer[new_line_number - 1] = new_content


def fix_clocks() -> None:
    buffer = vim.current.buffer
    fixes = bonipy.taskmd.fix_clocks(buffer)
    for line_number, new_clock_line in fixes:
        buffer[line_number - 1] = new_clock_line


def jump_to_started_clock() -> None:
    buffer = vim.current.buffer
    parsed_lines = bonipy.taskmd.to_parsed_lines(buffer)
    started_clocks = bonipy.taskmd.get_started_clocks(parsed_lines)

    if not started_clocks:
        print("No clock has been started.")
        return

    vim.current.window.cursor = (started_clocks[0]["line_number"], 0)

    if len(started_clocks) != 1:
        print(f"There ware {len(started_clocks)} started clocks.")


def set_timezone() -> None:
    timezone_as_string = typing.cast(str, vim.eval("input('Timezone: ')"))
    bonipy.taskmd.config.set_timezone(timezone_as_string)


def start_clock() -> None:
    buffer = vim.current.buffer
    now = bonipy.taskmd.get_now()

    parsed_lines = bonipy.taskmd.to_parsed_lines(buffer)
    new_parsed_line = bonipy.taskmd.end_first_clock(parsed_lines, now=now)
    if new_parsed_line:
        new_line_number = new_parsed_line["line_number"]
        new_content = bonipy.taskmd.to_string_from_parsed_line(new_parsed_line)
        buffer[new_line_number - 1] = new_content

    cursor_row = vim.current.window.cursor[0]  # First line is 1.
    parsed_lines = bonipy.taskmd.to_parsed_lines(buffer[:cursor_row])
    new_parsed_line = bonipy.taskmd.start_clock(parsed_lines, now=now)
    new_line_number = new_parsed_line["line_number"]
    new_content = bonipy.taskmd.to_string_from_parsed_line(new_parsed_line)
    buffer.append(new_content, new_line_number - 1)


class QuicklistRow(typing.TypedDict):
    bufnr: int
    lnum: int
    col: int
    text: str


class TimesheetArgument(typing.TypedDict):
    date: datetime.date
    days: int
    start: datetime.datetime


timesheet_argument = {
    "date": datetime.date.today(),
    "days": 1,
    "start": bonipy.taskmd.get_now(),
}  # type: TimesheetArgument


def write_agenda_to_qlist() -> None:
    date_as_string = vim.eval(f"input('Date: ', '{timesheet_argument['date']}')")
    assert isinstance(date_as_string, str)
    try:
        date = datetime.date.fromisoformat(date_as_string)
    except ValueError:
        print("Unable to parse given date.")
        return
    timesheet_argument["date"] = date

    start = datetime.datetime(
        year=date.year, month=date.month, day=date.day
    ).astimezone()
    end = start + datetime.timedelta(days=1)

    buffer = vim.current.buffer
    parsed_lines = bonipy.taskmd.to_parsed_lines(buffer)
    parsed_lines = bonipy.taskmd.bound_clocks(parsed_lines, start=start, end=end)
    parsed_lines = sorted(
        (parsed_line for parsed_line in parsed_lines if "clock" in parsed_line),
        key=lambda parsed_line: parsed_line["clock"]["start"],
    )
    parsed_lines_durations = bonipy.taskmd.get_parsed_line_durations(parsed_lines)
    if not parsed_lines_durations:
        print("No clocks found for agenda.")
        return

    total_duration = sum(
        (
            parsed_lines_duration["duration"]
            for parsed_lines_duration in parsed_lines_durations
            if "duration" in parsed_lines_duration
        ),
        start=datetime.timedelta(),
    )

    bufnr = vim.current.buffer.number
    quicklist_rows = [
        {
            "bufnr": bufnr,
            "col": 1,
            "lnum": 1,
            "text": f"Total: {total_duration}",
        }
    ]  # type: list[QuicklistRow]
    for parsed_line_duration in parsed_lines_durations:
        quicklist_rows.append(
            {
                "bufnr": bufnr,
                "col": 1,
                "lnum": parsed_line_duration["line_number"],
                "text": bonipy.taskmd.to_string_from_parsed_line(parsed_line_duration),
            }
        )

    vim.eval(f"setqflist({quicklist_rows})")
    vim.command(":copen")
    vim.command(":wincmd p")


# TODO: Refactor reports.
def write_day_report_to_qlist() -> None:
    date_as_string = vim.eval(f"input('Date: ', '{timesheet_argument['date']}')")
    assert isinstance(date_as_string, str)
    try:
        date = datetime.date.fromisoformat(date_as_string)
    except ValueError:
        print("Unable to parse given date.")
        return
    timesheet_argument["date"] = date

    start = datetime.datetime(
        year=date.year, month=date.month, day=date.day
    ).astimezone()
    end = start + datetime.timedelta(days=1)

    buffer = vim.current.buffer
    parsed_lines = bonipy.taskmd.to_parsed_lines(buffer)
    parsed_lines = bonipy.taskmd.bound_clocks(parsed_lines, start=start, end=end)
    parsed_line_durations = bonipy.taskmd.get_parsed_line_durations(parsed_lines)
    parsed_line_total_durations = bonipy.taskmd.get_parsed_line_total_durations(
        parsed_line_durations
    )
    summary_quicklist = bonipy.taskmd.get_summary_quicklist(parsed_line_total_durations)

    quicklist_rows = []  # type: list[QuicklistRow]
    bufnr = vim.current.buffer.number
    for summary_quicklist_item in summary_quicklist:
        quicklist_rows.append(
            {
                **summary_quicklist_item,
                "bufnr": bufnr,
                "col": 1,
            }
        )

    vim.eval(f"setqflist({quicklist_rows})")
    vim.command(":copen")
    vim.command(":wincmd p")


def write_month_report_to_qlist() -> None:
    date_as_string = vim.eval(f"input('Date: ', '{timesheet_argument['date']}')")
    assert isinstance(date_as_string, str)
    try:
        date = datetime.date.fromisoformat(date_as_string)
    except ValueError:
        print("Unable to parse given date.")
        return
    timesheet_argument["date"] = date

    start = datetime.datetime(year=date.year, month=date.month, day=1).astimezone()
    end = datetime.datetime(year=date.year, month=date.month + 1, day=1).astimezone()

    buffer = vim.current.buffer
    parsed_lines = bonipy.taskmd.to_parsed_lines(buffer)
    parsed_lines = bonipy.taskmd.bound_clocks(parsed_lines, start=start, end=end)
    parsed_line_durations = bonipy.taskmd.get_parsed_line_durations(parsed_lines)
    parsed_line_total_durations = bonipy.taskmd.get_parsed_line_total_durations(
        parsed_line_durations
    )
    summary_quicklist = bonipy.taskmd.get_summary_quicklist(parsed_line_total_durations)

    quicklist_rows = []  # type: list[QuicklistRow]
    bufnr = vim.current.buffer.number
    for summary_quicklist_item in summary_quicklist:
        quicklist_rows.append(
            {
                **summary_quicklist_item,
                "bufnr": bufnr,
                "col": 1,
            }
        )

    vim.eval(f"setqflist({quicklist_rows})")
    vim.command(":copen")
    vim.command(":wincmd p")


def write_summary_to_qlist() -> None:
    buffer = vim.current.buffer
    parsed_lines = bonipy.taskmd.to_parsed_lines(buffer)
    parsed_line_durations = bonipy.taskmd.get_parsed_line_durations(parsed_lines)
    parsed_line_total_durations = bonipy.taskmd.get_parsed_line_total_durations(
        parsed_line_durations
    )
    summary_quicklist = bonipy.taskmd.get_summary_quicklist(parsed_line_total_durations)

    quicklist_rows = []  # type: list[QuicklistRow]
    bufnr = vim.current.buffer.number
    for summary_quicklist_item in summary_quicklist:
        quicklist_rows.append(
            {
                **summary_quicklist_item,
                "bufnr": bufnr,
                "col": 1,
            }
        )

    vim.eval(f"setqflist({quicklist_rows})")
    vim.command(":copen")
    vim.command(":wincmd p")


def write_timesheet_to_qlist() -> None:
    date_as_string = vim.eval(f"input('Date: ', '{timesheet_argument['date']}')")
    assert isinstance(date_as_string, str)
    try:
        date = datetime.date.fromisoformat(date_as_string)
    except ValueError:
        print("Unable to parse given date.")
        return
    timesheet_argument["date"] = date

    start = datetime.datetime(year=date.year, month=date.month, day=1).astimezone()
    end = datetime.datetime(year=date.year, month=date.month + 1, day=1).astimezone()

    buffer = vim.current.buffer
    buffer_parsed_lines = bonipy.taskmd.to_parsed_lines(buffer)

    quicklist_rows = []  # type: list[QuicklistRow]
    bufnr = vim.current.buffer.number
    one_day = datetime.timedelta(days=1)
    day_start = start
    while day_start < end:
        day_end = day_start + one_day
        parsed_lines = bonipy.taskmd.bound_clocks(
            buffer_parsed_lines, start=day_start, end=day_end
        )
        parsed_line_durations = bonipy.taskmd.get_parsed_line_durations(parsed_lines)
        parsed_line_total_durations = bonipy.taskmd.get_parsed_line_total_durations(
            parsed_line_durations
        )
        summary_quicklist = bonipy.taskmd.get_summary_quicklist(
            parsed_line_total_durations
        )

        quicklist_rows.append(
            {
                "bufnr": bufnr,
                "col": 1,
                "lnum": 1,
                "text": str(day_start),
            }
        )
        for summary_quicklist_item in summary_quicklist:
            quicklist_rows.append(
                {
                    **summary_quicklist_item,
                    "bufnr": bufnr,
                    "col": 1,
                }
            )
        day_start = day_end

    vim.eval(f"setqflist({quicklist_rows})")
    vim.command(":copen")
    vim.command(":wincmd p")
