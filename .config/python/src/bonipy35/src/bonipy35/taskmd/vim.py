#!/usr/bin/env python3

# This is work in progress. Leaving in TODO as progress reminder.
# pylint: disable=fixme

# TODO: Summarise total time by topic.
# TODO: Summarise total time by time range.

# Standard libraries.
import copy
import datetime
import logging
import typing

# External dependencies.
import vim  # pylint: disable=import-error

# Internal modules.
from . import data

_logger = logging.getLogger(__name__)


def end_clock() -> None:
    buffer = vim.current.buffer
    parsed_document = data.ParsedDocument.parse(buffer)
    new_parsed_line = parsed_document.end_first_clock()
    if not new_parsed_line:
        print("No clock has been started.")
        return

    buffer[new_parsed_line.line_number - 1] = new_parsed_line.to_string()


def fix_clocks() -> None:
    buffer = vim.current.buffer
    parsed_document = data.ParsedDocument.parse(buffer)
    fixes = parsed_document.get_fix_clocks_diff()
    for line_number, new_clock_line in fixes:
        buffer[line_number - 1] = new_clock_line


def jump_to_started_clock() -> None:
    buffer = vim.current.buffer
    parsed_document = data.ParsedDocument.parse(buffer)
    started_clocks = list(parsed_document.get_started_clocks())

    if not started_clocks:
        print("No clock has been started.")
        return

    vim.current.window.cursor = (started_clocks[0].line_number, 0)

    if len(started_clocks) != 1:
        print(f"There ware {len(started_clocks)} started clocks.")


def set_timezone() -> None:
    timezone_as_string = typing.cast(str, vim.eval("input('Timezone: ')"))
    data.config.set_timezone(timezone_as_string)


def start_clock() -> None:
    buffer = vim.current.buffer
    now = data.get_now()

    parsed_document = data.ParsedDocument.parse(buffer)
    new_parsed_line = parsed_document.end_first_clock(now=now)
    if new_parsed_line:
        new_line_number = new_parsed_line.line_number
        buffer[new_line_number - 1] = new_parsed_line.to_string()

    cursor_row = vim.current.window.cursor[0]  # First line is 1.
    new_parsed_line = parsed_document.start_clock(line_number=cursor_row, now=now)
    new_line_number = new_parsed_line.line_number
    buffer.append(new_parsed_line.to_string(), new_line_number - 1)


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
    "start": data.get_now(),
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
    parsed_document = data.ParsedDocument.parse(buffer)
    parsed_document.bound_time_range(start=start, end=end)
    parsed_lines = parsed_document.parsed_lines

    timestamp_lines = []  # type: list[tuple[datetime.datetime, data.ParsedLine]]
    total_duration = datetime.timedelta()
    for parsed_line in parsed_lines:
        clock = parsed_line.clock
        if clock is None:
            continue

        clock_end = clock.end
        if clock_end is None:
            continue

        clock_start = clock.start
        total_duration += clock_end - clock_start
        timestamp_lines.append((clock_start, parsed_line))

    bufnr = vim.current.buffer.number
    quicklist_rows = [
        {
            "bufnr": bufnr,
            "col": 1,
            "lnum": 1,
            "text": f"Total: {total_duration}",
        }
    ]  # type: list[QuicklistRow]
    for timestamp_line in sorted(
        timestamp_lines, key=lambda timestamp_line: timestamp_line[0]
    ):
        parsed_line = timestamp_line[1]
        quicklist_rows.append(
            {
                "bufnr": bufnr,
                "col": 1,
                "lnum": parsed_line.line_number,
                "text": parsed_line.to_string(),
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
    parsed_document = data.ParsedDocument.parse(buffer)
    parsed_document.bound_time_range(start=start, end=end)
    parsed_document.refresh_durations()
    summary_quicklist = data.get_summary_quicklist(parsed_document)

    bufnr = vim.current.buffer.number
    quicklist_rows = [
        QuicklistRow(
            bufnr=bufnr,
            col=1,
            lnum=summary_quicklist_item.lnum,
            text=summary_quicklist_item.text,
        )
        for summary_quicklist_item in summary_quicklist
    ]

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
    parsed_document = data.ParsedDocument.parse(buffer)
    parsed_document.bound_time_range(start=start, end=end)
    parsed_document.refresh_durations()
    summary_quicklist = data.get_summary_quicklist(parsed_document)

    bufnr = vim.current.buffer.number
    quicklist_rows = [
        QuicklistRow(
            bufnr=bufnr,
            col=1,
            lnum=summary_quicklist_item.lnum,
            text=summary_quicklist_item.text,
        )
        for summary_quicklist_item in summary_quicklist
    ]

    vim.eval(f"setqflist({quicklist_rows})")
    vim.command(":copen")
    vim.command(":wincmd p")


def write_summary_to_qlist() -> None:
    buffer = vim.current.buffer
    parsed_document = data.ParsedDocument.parse(buffer)
    parsed_document.refresh_durations()
    summary_quicklist = data.get_summary_quicklist(parsed_document)

    bufnr = vim.current.buffer.number
    quicklist_rows = [
        QuicklistRow(
            bufnr=bufnr,
            col=1,
            lnum=summary_quicklist_item.lnum,
            text=summary_quicklist_item.text,
        )
        for summary_quicklist_item in summary_quicklist
    ]

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
    buffer_parsed_document = data.ParsedDocument.parse(buffer)

    quicklist_rows = []  # type: list[QuicklistRow]
    bufnr = vim.current.buffer.number
    one_day = datetime.timedelta(days=1)
    day_start = start
    while day_start < end:
        day_end = day_start + one_day
        parsed_document = copy.deepcopy(buffer_parsed_document)
        parsed_document.bound_time_range(start=day_start, end=day_end)
        parsed_document.refresh_durations()
        summary_quicklist = data.get_summary_quicklist(parsed_document)

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
                QuicklistRow(
                    bufnr=bufnr,
                    col=1,
                    lnum=summary_quicklist_item.lnum,
                    text=summary_quicklist_item.text,
                )
            )
        day_start = day_end

    vim.eval(f"setqflist({quicklist_rows})")
    vim.command(":copen")
    vim.command(":wincmd p")
