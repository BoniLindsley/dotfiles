#!/usr/bin/env python3

# Need Python 3.6. Supporting Python 3.5.
# pylint: disable=consider-using-f-string

# Standard libraries.
import argparse
import contextlib
import datetime
import logging
import re
import sys
import typing

from typing import Generator


_logger = logging.getLogger(__name__)

Title = typing.NamedTuple(
    "Title",
    [
        ("level", int),
        ("state", str),
        ("priority", str),
        ("content", str),
        ("tags", "list[str]"),
    ],
)

_to_title_regex = re.compile(
    "(?P<level>#+)"
    "(( +)((?P<state>DONE|TODO)))?"
    r"(( +)(\[#(?P<priority>.)\]))?"
    "( +)(?P<content>.*?)"
    "(( +)(?P<tags>(:[0-9:@A-Z_a-z]+:)?))?$"
)


def to_title(source: str) -> "None | Title":
    title_match = _to_title_regex.match(source)
    if not title_match:
        return None

    level_source = title_match.group("level")
    level = len(level_source)

    state = title_match.group("state") or ""
    priority = title_match.group("priority") or ""

    content = title_match.group("content")

    # Split up tags but only keep non-empty tag values.
    # Note that `:a:b:c::e:".split(":") == ["", "a", "b", "c", "", "e", ""]`.
    # The tags to keep are the non-empty strings.
    tags_source = title_match.group("tags") or ""
    tags = list(filter(None, tags_source.split(":")))

    return Title(
        level=level, state=state, priority=priority, content=content, tags=tags
    )


def to_datetime(source: str) -> "None | datetime.datetime":
    try:
        return datetime.datetime.strptime(source, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


Clock = typing.NamedTuple(
    "Clock",
    [
        ("start", datetime.datetime),
        ("end", datetime.datetime),
    ],
)


_to_clock_regex = re.compile(
    r"CLOCK:\s+\[(?P<begin>[0-9+\-:T]+)\]--\[(?P<end>[0-9+\-:T]+)\]"
)


def to_clock(source: str) -> "None | Clock":
    clock_match = _to_clock_regex.match(source)
    if not clock_match:
        return None

    begin_source = clock_match.group("begin")
    end_source = clock_match.group("end")

    begin = to_datetime(begin_source)
    end = to_datetime(end_source)

    if not begin or not end:
        return None

    return Clock(begin, end)


Token = "Clock | Title"  # type: typing.TypeAlias # pylint: disable=invalid-name


def create_markdown_parser() -> Generator["None | Token", str, None]:
    line = yield None
    while True:
        title = to_title(line)
        if title is not None:
            line = yield title
            continue
        if line != "```org.logbook":
            line = yield None
            continue
        while line != "```":
            line = yield to_clock(line)
        line = yield None


DEFAULT_BUFFER_SIZE = 4096


def read_lines(
    *, buffer_size: "None | int" = None, source: typing.TextIO
) -> Generator[str, None, None]:
    if buffer_size is None:
        buffer_size = DEFAULT_BUFFER_SIZE
    if buffer_size <= 0:
        return
    while True:
        line = source.readline(buffer_size)
        # Empty line if at EOF.
        if not line:
            return
        if len(line) >= buffer_size:
            _logger.error("Line too long.")
            return
        # Note that line always has a trailing new line unless ending in EOF.
        # TODO: Check line ending of source. Strip line ending before yielding line.
        yield line[:-1]


Entry = typing.NamedTuple(
    "Entry",
    [
        ("title", Title),
        ("clocks", "list[Clock]"),
        ("children", "list[Entry]"),
    ],
)


def create_token_parser() -> Generator["None | Entry", Token, "None | Entry"]:
    entry = Entry(
        title=Title(level=0, state="", priority="", content="", tags=[]),
        clocks=[],
        children=[],
    )

    response = None
    while True:
        try:
            token = yield response
        except GeneratorExit:
            return entry
        response = None

        if isinstance(token, Clock):
            entry.clocks.append(token)
            continue

        response = entry
        entry = Entry(title=token, clocks=[], children=[])


# TODO: Consider using recursive yield from.
def create_entry_parser() -> Generator[None, Entry, Entry]:
    try:
        base_entry = entry = yield None
    except GeneratorExit:
        # Use default entry.
        return Entry(
            title=Title(level=0, state="", priority="", content="", tags=[]),
            clocks=[],
            children=[],
        )

    if not base_entry.title.level:
        raise RuntimeError("First entry must have a level 0 title.")

    while True:
        try:
            entry = yield None
        except GeneratorExit:
            return base_entry

        parent = base_entry

        level = entry.level
        while parent.children:
            child = parent.children[-1]
            if child.title.level >= level:
                break
            parent = child

        entry = Entry(title=markdown_line, clocks=[], children=[])
        parent.children.append(entry)


def create_document_parser() -> Generator[None, str, Entry]:
    document = entry = Entry(
        title=Title(level=0, state="", priority="", content="", tags=[]),
        clocks=[],
        children=[],
    )

    markdown_parser = create_markdown_parser()
    try:
        next(markdown_parser)
    except StopIteration:
        return document

    while True:
        try:
            line = yield None
        except GeneratorExit:
            return document

        markdown_line = markdown_parser.send(line)
        if markdown_line is None:
            continue
        if isinstance(markdown_line, Clock):
            entry.clocks.append(markdown_line)
            continue

        parent = document

        level = markdown_line.level
        while parent.children:
            child = parent.children[-1]
            if child.title.level >= level:
                break
            parent = child

        entry = Entry(title=markdown_line, clocks=[], children=[])
        parent.children.append(entry)


def parse_document(source: typing.TextIO) -> Entry:
    # Initialise parser.
    document_parser = create_document_parser()
    next(document_parser)

    # Parser every line.
    for line in source:
        document_parser.send(line)

    # Get return value from parser.
    try:
        document_parser.throw(GeneratorExit())
    except StopIteration as error:
        return error.value  # type: ignore[no-any-return]

    return Entry(
        title=Title(level=0, state="", priority="", content="", tags=[]),
        clocks=[],
        children=[],
    )


MarkdownLines = "list[Token]"  # type: typing.TypeAlias # pylint: disable=invalid-name


def read_markdown_lines() -> MarkdownLines:
    markdown_parser = create_markdown_parser()
    next(markdown_parser)
    markdown_lines = []
    for line in read_lines(source=sys.stdin):
        result = markdown_parser.send(line)
        if result is None:
            continue
        markdown_lines.append(result)
    return markdown_lines


def print_duration(duration: datetime.timedelta) -> str:
    if not duration:
        return ""

    hours = duration / datetime.timedelta(hours=1)
    return "{hours:.2f}h".format(hours=hours)


LogRow = typing.NamedTuple(
    "LogRow",
    [
        ("duration", str),
        ("headline", str),
    ],
)
LogTable = "list[LogRow]"  # type: typing.TypeAlias # pylint: disable=invalid-name


def to_log_table(markdown_lines: MarkdownLines) -> LogTable:
    log_table = []

    # Store total duration in the first line as summary.
    # It will be filled again before returning.
    total_duration = datetime.timedelta()
    duration = datetime.timedelta()
    content = "Title"

    def add_row() -> None:
        log_table.append(LogRow(print_duration(duration), content))

    indent = "  "
    for line in markdown_lines:
        if isinstance(line, Title):
            add_row()
            content = indent * (line.level - 1) + line.content
            duration = datetime.timedelta()
            continue

        clock_duration = line.end - line.start
        duration += clock_duration
        total_duration += clock_duration

    add_row()

    log_table[0] = LogRow(print_duration(total_duration), log_table[0].headline)

    return log_table


def print_log_table(log_table: LogTable) -> "list[str]":
    if not log_table:
        return []

    row_format = "|"
    row_separator = "+"

    duration_heading = "Duration"
    max_duration_length = max(len(log_row.duration) for log_row in log_table)
    max_duration_length = max(max_duration_length, len(duration_heading))
    row_format += " {duration:>"
    row_format += str(max_duration_length)
    row_format += "} |"
    row_separator += "-" * max_duration_length
    row_separator += "--+"

    headline_heading = "Headline"
    max_headline_length = max(len(log_row.headline) for log_row in log_table)
    max_headline_length = max(max_headline_length, len(headline_heading))
    row_format += " {headline:"
    row_format += str(max_headline_length)
    row_format += "} |"
    row_separator += "-" * max_headline_length
    row_separator += "--+"

    output = [
        row_format.format(duration=duration_heading, headline=headline_heading),
        row_separator,
    ]
    for log_row in log_table:
        output.append(
            row_format.format(duration=log_row.duration, headline=log_row.headline)
        )

    return output


@contextlib.contextmanager
def suppress_keyboard_interrupt() -> Generator[None, None, None]:
    try:
        yield
    except KeyboardInterrupt:
        # Clear line echo-ing "^C".
        print()


def parse_arguments(args: "list[str]") -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["report"], default="report")
    return parser.parse_args(args)


# TODO: Add command for log mode. Ordered by time. Base case for daily view.
# TODO: Add command for report mode. Ordered by title.
# TODO: Add command for checking clock gaps.
# TODO: Add option to prefix by filename:lineno for Vim quickfix jumps.


@suppress_keyboard_interrupt()
def main(argv: "None | list[str]" = None) -> int:
    if argv is None:
        argv = sys.argv

    arguments = parse_arguments(argv[1:])

    markdown_lines = read_markdown_lines()

    if arguments.command == "report":
        log_table = to_log_table(markdown_lines)
        for row in print_log_table(log_table):
            print(row)

    return 0


if __name__ == "__main__":
    sys.exit(main())
