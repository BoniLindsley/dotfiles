#!/usr/bin/env python3

# This is work in progress. Leaving in TODO as progress reminder.
# pylint: disable=fixme

# TODO: Summarise total time by topic.
# TODO: Summarise total time by time range.

# Standard libraries.
import argparse
import collections
import contextlib
import copy
import datetime
import logging
import re
import sys
import typing

# TODO(Python 3.9): Use collections.abc version.
from typing import Generator, Iterator

# TODO(Python 3.9): Use builtin.
from typing import Dict, List, Tuple

# TODO(Python 3.10): Use | instead of Union.
from typing import Union

# ========
# Common code
# ========


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
    *, logger: logging.Logger, verbosity: Union[None, int] = None
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
    *, buffer_size: Union[None, int] = None, source: typing.TextIO
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


# ========
# Actual implementation
# ========

# Headlines must have a space after the leading characters.
to_headline_required_regex = re.compile(r"#+\s+")

to_headline_regex = re.compile(
    r"(?P<level>#+)"
    r"(\s+(?P<keyword>DONE|TODO))?"
    r"(\s+(\[#(?P<priority>.)\]))?"
    r"(\s+(?P<comment>COMMENT))?"
    r"(\s+(?P<title>.+?))?"
    r"(\s+(?P<tags>:[\w@:]+:))?"
    r"\s*$"
)


class HeadlineRequired(typing.TypedDict):
    level: int


class Headline(HeadlineRequired, total=False):
    keyword: str
    priority: str
    comment: bool
    title: str
    tags: List[str]


def to_headline(line: str) -> Union[None, Headline]:
    match = to_headline_required_regex.match(line)
    if not match:
        return None

    match = to_headline_regex.match(line)
    if not match:
        return None

    headline = {"level": len(match["level"])}  # type: Headline

    keyword = match["keyword"]
    if keyword is not None:
        headline["keyword"] = keyword

    priority = match["priority"]
    if priority is not None:
        headline["priority"] = priority

    comment = match["comment"]
    if comment is not None:
        headline["comment"] = bool(comment)

    title = match["title"]
    if title is not None:
        headline["title"] = title

    tags_unparsed = match["tags"]
    if tags_unparsed is not None:
        tags = list(filter(None, tags_unparsed.split(":")))
        if tags:
            headline["tags"] = tags

    return headline


def to_string_from_headline(headline: Headline) -> str:
    level_as_string = "#" * headline["level"]

    keyword_as_string = headline.get("keyword")

    priority_as_string = None
    priority = headline.get("priority")
    if priority:
        priority_as_string = "[#" + priority + "]"

    comment_as_string = "COMMENT" if "comment" in headline else None

    title_as_string = headline.get("title")

    tags_as_string = None
    tags = headline.get("tags")
    if tags:
        tags_as_string = ":".join(filter(None, tags))
    if tags_as_string:
        tags_as_string = ":" + tags_as_string + ":"

    content_parts = tuple(
        filter(
            None,
            (
                level_as_string,
                keyword_as_string,
                priority_as_string,
                comment_as_string,
                title_as_string,
                tags_as_string,
            ),
        )
    )

    if len(content_parts) == 1:
        content_as_string = content_parts[0] + " "
    else:
        content_as_string = " ".join(content_parts)

    return content_as_string


to_clock_regex = re.compile(
    # "CLOCK: (2024-11-12T00:00:00+00:00)"
    r"CLOCK:\s+"
    r"\((?P<start>[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+[+-][0-9]+:?[0-9]+)\)"
    # "--(2025-11-12T00:01:00+00:00)": Optional
    r"(--\((?P<end>[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+[+-][0-9]+:?[0-9]+)\))?"
)


class ClockRequired(typing.TypedDict):
    start: datetime.datetime


class Clock(ClockRequired, total=False):
    end: datetime.datetime


def to_clock(title: str) -> Union[None, Clock]:
    match = to_clock_regex.match(title)
    if not match:
        return None

    clock = {
        "start": datetime.datetime.strptime(match["start"], "%Y-%m-%dT%H:%M:%S%z"),
    }  # type: Clock

    end = match["end"]
    if end is not None:
        clock["end"] = datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M:%S%z")

    return clock


def to_string_from_clock(clock: Clock) -> str:
    start = clock["start"]
    start_string = start.strftime("%Y-%m-%dT%H:%M:%S%z")

    clock_line = "CLOCK: (" + start_string + ")"

    if "end" in clock:
        end = clock["end"]
        end_string = end.strftime("%Y-%m-%dT%H:%M:%S%z")
        duration = end - start
        duration_string = str(duration)

        clock_line += "--" "(" + end_string + ")" " => " + duration_string

    return clock_line


class ParsedLineRequired(typing.TypedDict):
    line_number: int
    content: str


class ParsedLine(ParsedLineRequired, total=False):
    headline: Headline
    clock: Clock


def to_parsed_lines(lines: List[str]) -> List[ParsedLine]:
    is_inside_code_block = False

    parsed_lines = []  # type: list[ParsedLine]
    for line_number, line in enumerate(lines, start=1):
        parsed_line = {
            "line_number": line_number,
            "content": line,
        }  # type: ParsedLine
        parsed_lines.append(parsed_line)

        if is_inside_code_block:
            if line == "```":
                is_inside_code_block = False
            continue
        if line.startswith("```"):
            is_inside_code_block = True
            continue

        headline = to_headline(line)
        if not headline:
            continue
        parsed_line["headline"] = headline

        clock = to_clock(headline["title"])
        if not clock:
            continue
        parsed_line["clock"] = clock

    return parsed_lines


def to_string_from_parsed_line(parsed_line: ParsedLine) -> str:
    title_as_string = None
    clock = parsed_line.get("clock")
    if clock:
        title_as_string = to_string_from_clock(clock)

    headline = parsed_line.get("headline")
    if title_as_string:
        level = 1
        if headline:
            level = headline["level"]

        headline = {
            "level": level,
            "title": title_as_string,
        }

    content_as_string = None
    if headline:
        content_as_string = to_string_from_headline(headline)

    if not content_as_string:
        content_as_string = parsed_line["content"]

    return content_as_string


class Config:
    def __init__(self) -> None:
        self.timezone = None  # type: Union[None, datetime.timezone]

    def set_timezone(self, timezone_as_string: str) -> None:
        if not timezone_as_string:
            self.timezone = None
            return

        is_negative = False
        assert isinstance(timezone_as_string, str)
        if timezone_as_string[0] == "+":
            timezone_as_string = timezone_as_string[1:]
        elif timezone_as_string[0] == "-":
            is_negative = True
            timezone_as_string = timezone_as_string[1:]

        if not timezone_as_string:
            self.timezone = None
            return

        if len(timezone_as_string) <= 2:
            timezone_hour = int(timezone_as_string)
            timezone_minute = 0
        else:
            timezone_hour = int(timezone_as_string[:2])
            timezone_minute = int(timezone_as_string[2:])

        if is_negative:
            timezone_hour *= -1

        self.timezone = datetime.timezone(
            datetime.timedelta(hours=timezone_hour, minutes=timezone_minute)
        )


config = Config()


def get_now() -> datetime.datetime:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .astimezone(tz=config.timezone)
        .replace(microsecond=0)
    )


# TODO: Add unit test.
def bound_clocks(
    parsed_lines: List[ParsedLine], *, start: datetime.datetime, end: datetime.datetime
) -> List[ParsedLine]:
    new_parsed_lines = []  # type: list[ParsedLine]
    for parsed_line in parsed_lines:
        new_parsed_line = copy.deepcopy(parsed_line)
        clock = new_parsed_line.get("clock")
        if clock:
            clock_start = clock["start"]
            if clock_start >= end:
                continue
            if clock_start < start:
                clock["start"] = start

            clock_end = clock.get("end")
            if clock_end:
                if clock_end <= start:
                    continue
                if clock_end > end:
                    clock["end"] = end
        new_parsed_lines.append(new_parsed_line)
    return new_parsed_lines


def end_first_clock(
    parsed_lines: List[ParsedLine], *, now: datetime.datetime
) -> Union[None, ParsedLine]:
    for parsed_line in parsed_lines:
        clock = parsed_line.get("clock")
        if not clock:
            continue

        if "end" in clock:
            continue

        new_parsed_line = copy.deepcopy(parsed_line)
        new_parsed_line["clock"]["end"] = now
        return new_parsed_line

    return None


def fix_clocks(lines: List[str]) -> List[Tuple[int, str]]:
    fixes = []  # type: list[tuple[int, str]]

    last_level = 0

    headlines = HeadlineParser.parse_all(stdin=iter(lines))
    for line_number, headline_entries in headlines.items():
        if "level" in headline_entries:
            headline = typing.cast(Headline, headline_entries)
            last_level = headline["level"]

        if "start" not in headline_entries:
            continue

        clock = typing.cast(Clock, headline_entries)
        new_clock_line = to_string_from_clock(clock)
        fixes.append((line_number, "#" * (last_level + 1) + " " + new_clock_line))

    return fixes


def start_clock(
    parsed_lines: List[ParsedLine], *, now: datetime.datetime
) -> ParsedLine:
    for parsed_line in reversed(parsed_lines):
        if "clock" in parsed_line:
            continue

        headline = parsed_line.get("headline")
        if not headline:
            continue

        new_line_number = parsed_line["line_number"] + 1
        new_clock_level = headline["level"] + 1
        break
    else:
        new_clock_level = 1
        new_line_number = 1

    return {
        "line_number": new_line_number,
        "content": "",
        "headline": {
            "level": new_clock_level,
        },
        "clock": {
            "start": now,
        },
    }


class ParsedLineDuration(ParsedLine):
    duration: datetime.timedelta


# TODO: Add unit test.
def get_parsed_line_durations(
    parsed_lines: List[ParsedLine],
) -> List[ParsedLineDuration]:
    parsed_line_durations = []  # type: list[ParsedLineDuration]
    for parsed_line in parsed_lines:
        parsed_line_duration = {
            **copy.deepcopy(parsed_line),
            "duration": datetime.timedelta(),
        }  # type: ParsedLineDuration
        parsed_line_durations.append(parsed_line_duration)

        clock = parsed_line.get("clock")
        if clock:
            end = clock.get("end")
            if end:
                parsed_line_duration["duration"] = end - clock["start"]

    return parsed_line_durations


class ParsedLineTotalDuration(ParsedLineDuration):
    total_duration: datetime.timedelta


# TODO: Add unit test.
def get_parsed_line_total_durations(
    parsed_line_durations: List[ParsedLineDuration],
) -> List[ParsedLineTotalDuration]:
    parsed_line_total_durations = []  # type: list[ParsedLineTotalDuration]

    # Level zero is root.
    child_level_durations = [datetime.timedelta()]
    for parse_line_duration in reversed(parsed_line_durations):
        parsed_line_total_duration = {
            **parse_line_duration,
            "total_duration": parse_line_duration["duration"],
        }  # type: ParsedLineTotalDuration
        parsed_line_total_durations.append(parsed_line_total_duration)

        headline = parsed_line_total_duration.get("headline")
        if not headline:
            continue

        level = headline["level"]
        parsed_line_total_duration["total_duration"] = sum(
            child_level_durations[level + 1 :],
            start=parsed_line_total_duration["total_duration"],
        )

        missing_levels = level + 1 - len(child_level_durations)
        if missing_levels > 0:
            child_level_durations += [datetime.timedelta()] * missing_levels
        else:
            child_level_durations = child_level_durations[: level + 1]
        child_level_durations[level] += parsed_line_total_duration["total_duration"]

    parsed_line_total_durations.append(
        {
            "line_number": 1,
            "content": "",
            "headline": {
                "level": 0,
            },
            "duration": datetime.timedelta(),
            "total_duration": sum(
                child_level_durations,
                start=datetime.timedelta(),
            ),
        }
    )

    return list(reversed(parsed_line_total_durations))


class QuicklistItem(typing.TypedDict):
    lnum: int
    text: str


# TODO: Add unit test.
def get_summary_quicklist(
    parsed_line_total_durations: List[ParsedLineTotalDuration],
) -> List[QuicklistItem]:
    quicklist = [
        {
            "lnum": 1,
            "text": "| Duration / h | Headline",
        }
    ]  # type: List[QuicklistItem]

    hour = datetime.timedelta(hours=1)
    for parsed_line_total_duration in parsed_line_total_durations:
        total_duration = parsed_line_total_duration["total_duration"]
        if not total_duration:
            continue

        headline = parsed_line_total_duration.get("headline")
        if not headline:
            continue

        title = headline.get("title")
        if not title:
            title = parsed_line_total_duration["content"]

        level = headline["level"]
        if level:
            title = "#" * level + " " + title
        elif title:
            title = f"Total: {title}"
        else:
            title = "Total"

        quicklist.append(
            {
                "lnum": parsed_line_total_duration["line_number"],
                "text": f"| {total_duration / hour:>12.2f} | {title}",
            }
        )

    return quicklist


######


class HeadlineParser:
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.is_inside_code_block = False
        self.line_number = 0

    def send(self, line: str) -> Union[None, Tuple[int, "Clock | Headline"]]:
        self.line_number += 1

        if self.is_inside_code_block:
            if line == "```":
                self.is_inside_code_block = False
            return None
        if line.startswith("```"):
            self.is_inside_code_block = True
            return None

        headline = to_headline(line)
        if not headline:
            return None

        clock = to_clock(headline["title"])
        if not clock:
            return self.line_number, headline

        return self.line_number, clock

    @classmethod
    def parse_all(cls, *, stdin: Iterator[str]) -> Dict[int, "Clock | Headline"]:
        headline_parser = cls()
        headlines = {}  # type: dict[int, Clock | Headline]
        for line in stdin:
            result = headline_parser.send(line)
            if result is None:
                continue
            line_number, headline_item = result
            headlines[line_number] = headline_item
        return headlines


class HeadlineDuration(Headline):
    duration: datetime.timedelta
    line_number: int


def get_headline_durations(
    headlines: "dict[int, Clock | Headline]",
) -> List[HeadlineDuration]:
    last_headline_duration = {
        "level": 0,
        "duration": datetime.timedelta(),
        "line_number": 1,
    }  # type: HeadlineDuration
    headline_durations = [last_headline_duration]
    for line_number, headline_item in headlines.items():
        try:
            start = headline_item["start"]  # type: ignore[typeddict-item]
            end = headline_item["end"]  # type: ignore[typeddict-item]
        except KeyError:
            headline = headline_item  # type: Headline  # type: ignore[assignment]
            last_headline_duration = {
                **headline,
                "duration": datetime.timedelta(),
                "line_number": line_number,
            }
            headline_durations.append(last_headline_duration)
        else:
            duration = end - start
            last_headline_duration["duration"] += duration
    return headline_durations


class HeadlineTotalDuration(HeadlineDuration):
    total_duration: datetime.timedelta


def sum_durations(
    headline_durations: List[HeadlineDuration],
) -> "collections.deque[HeadlineTotalDuration]":
    summed_durations = (
        collections.deque()
    )  # type: collections.deque[HeadlineTotalDuration]
    # Level zero is root.
    child_level_durations = [datetime.timedelta()]
    for headline_duration in reversed(headline_durations):
        level = headline_duration["level"]
        total_duration = sum(
            child_level_durations[level + 1 :], start=headline_duration["duration"]
        )
        summed_durations.appendleft(
            {
                **headline_duration,
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
    headlines = HeadlineParser.parse_all(stdin=read_lines(source=stdin))
    headline_durations = get_headline_durations(headlines)
    summed_durations = sum_durations(headline_durations)
    summed_durations = collections.deque(
        filter(
            lambda headline_total_duration: headline_total_duration["total_duration"],
            summed_durations,
        )
    )
    hour = datetime.timedelta(hours=1)
    print("Duration / h | Headline", file=stdout)
    for headline_total_duration in summed_durations:
        if headline_total_duration["total_duration"]:
            level = headline_total_duration["level"]
            title = headline_total_duration.get("title", "")
            if level:
                title = "  " * (level - 1) + "* " + title
            else:
                title = f"Total: {title}" if title else "Total"
            print(
                f"{headline_total_duration['total_duration'] / hour:>12.2f} | {title}",
                file=stdout,
            )
    return 0


def parse_arguments(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_verbose_flag(parser)
    return parser.parse_args(args)


@suppress_keyboard_interrupt()
def main(argv: Union[None, List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv

    set_up_logging(logger=_logger)

    arguments = parse_arguments(argv[1:])
    set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    return run(stdin=sys.stdin, stdout=sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
