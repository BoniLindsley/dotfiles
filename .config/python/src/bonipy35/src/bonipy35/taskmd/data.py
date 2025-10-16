#!/usr/bin/env python3

# Need Python 3.5 support.
# pylint: disable=consider-using-f-string
# Need Python 3.5 support.
# pylint: disable=too-many-arguments

# Standard libraries.
import datetime
import logging
import pathlib
import re
import typing

from typing import Iterator, List, Tuple, Union

_logger = logging.getLogger(__name__)


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


class Headline:
    parse_regex = re.compile(
        r"(?P<level>#+)"
        r"(\s+(?P<keyword>DONE|TODO))?"
        r"(\s+(\[#(?P<priority>.)\]))?"
        r"(\s+(?P<comment>COMMENT))?"
        r"(\s+(?P<title>.+?))?"
        r"(\s+(?P<tags>:[\w@:]+:))?"
        r"\s*$"
    )

    def __init__(
        self,
        *args: typing.Any,
        comment: Union[None, bool] = None,
        keyword: Union[None, str] = None,
        level: int,
        priority: Union[None, str] = None,
        tags: Union[None, List[str]] = None,
        title: Union[None, str] = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        if comment is None:
            comment = False

        self.comment = comment
        self.keyword = keyword
        self.level = level
        self.priority = priority
        self.tags = tags
        self.title = title

    @classmethod
    def parse(cls, line: str) -> "None | typing.Self":
        match = cls.parse_regex.match(line)
        if not match:
            return None

        self = cls(
            comment=bool(match.group("comment")),
            keyword=match.group("keyword"),
            level=len(match.group("level")),
            priority=match.group("priority"),
            title=match.group("title"),
        )

        tags_unparsed = match.group("tags")
        if tags_unparsed is not None:
            tags = list(filter(None, tags_unparsed.split(":")))
            if tags:
                self.tags = tags

        return self

    def to_string(self) -> str:
        tags_as_string = None
        tags = self.tags
        if tags:
            tags_as_string = ":".join(filter(None, tags))
        if tags_as_string:
            tags_as_string = ":" + tags_as_string + ":"

        priority = self.priority
        line_parts = list(
            filter(
                None,
                (
                    "#" * self.level,
                    self.keyword,
                    "[#" + priority + "]" if priority else None,
                    "COMMENT" if self.comment else None,
                    self.title,
                    tags_as_string,
                ),
            )
        )

        if len(line_parts) == 1:
            line_parts.append("")

        line = " ".join(line_parts)
        return line


class Clock:
    parse_regex = re.compile(
        # "CLOCK: (2024-11-12T00:00:00+00:00)"
        r"CLOCK:\s+"
        r"\((?P<start>[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+[+-][0-9]+:?[0-9]+)\)"
        # "--(2025-11-12T00:01:00+00:00)": Optional
        r"(--\((?P<end>[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+[+-][0-9]+:?[0-9]+)\))?"
    )

    def __init__(
        self,
        *args: typing.Any,
        end: Union[None, datetime.datetime] = None,
        start: datetime.datetime,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.end = end
        self.start = start

    def bound_time_range(
        self, *, start: datetime.datetime, end: datetime.datetime
    ) -> None:
        clock_start = self.start
        if clock_start <= start:
            self.start = start
        elif clock_start >= end:
            self.start = end

        clock_end = self.end
        if clock_end is None:
            pass
        elif clock_end <= start:
            self.end = start
        elif clock_end >= end:
            self.end = end

    def get_duration(self) -> datetime.timedelta:
        end = self.end
        if end is None:
            return datetime.timedelta()

        return end - self.start

    @classmethod
    def parse(cls, line: str) -> "None | typing.Self":
        match = cls.parse_regex.match(line)
        if not match:
            return None

        start_unparsed = match.group("start")
        start = datetime.datetime.strptime(start_unparsed, "%Y-%m-%dT%H:%M:%S%z")

        end_unparsed = match.group("end")
        end = (
            datetime.datetime.strptime(end_unparsed, "%Y-%m-%dT%H:%M:%S%z")
            if end_unparsed is not None
            else None
        )

        self = cls(
            end=end,
            start=start,
        )

        return self

    def to_string(self) -> str:
        start = self.start
        start_string = start.strftime("%Y-%m-%dT%H:%M:%S%z")

        line_parts = ["CLOCK: (", start_string, ")"]

        end = self.end
        if end is not None:
            end_string = end.strftime("%Y-%m-%dT%H:%M:%S%z")
            duration = end - start
            duration_string = str(duration)
            line_parts.extend(("--(", end_string, ") => ", duration_string))

        line_as_string = "".join(line_parts)
        return line_as_string


class ParsedLine:
    def __init__(
        self,
        *args: typing.Any,
        clock: Union[None, Clock] = None,
        duration: Union[None, datetime.timedelta] = None,
        headline: Union[None, Headline] = None,
        line: str,
        line_number: int,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        if duration is None:
            duration = datetime.timedelta()

        self.clock = clock
        self.duration = duration
        self.headline = headline
        self.line = line
        self.line_number = line_number

    def get_duration(self) -> datetime.timedelta:
        clock = self.clock
        if not clock:
            return self.duration
        end = clock.end
        if not end:
            return self.duration
        duration = end - clock.start
        return duration

    def reparse_line(self) -> None:
        headline = self.headline = Headline.parse(self.line)
        if headline is None:
            return

        title = headline.title
        if title is None:
            return

        self.clock = Clock.parse(title)

    def to_string(self) -> str:
        title = None
        clock = self.clock
        if clock:
            title = clock.to_string()

        headline = self.headline
        if title:
            level = 1
            if headline:
                level = headline.level

            headline = Headline(
                level=level,
                title=title,
            )

        if headline:
            line = headline.to_string()
        else:
            line = self.line

        return line


class ParsedDocument:
    def __init__(
        self,
        *args: typing.Any,
        parsed_lines: Union[None, List[ParsedLine]] = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        if parsed_lines is None:
            parsed_lines = []

        self.duration = datetime.timedelta()
        self.parsed_lines = parsed_lines

    def bound_time_range(
        self, *, start: datetime.datetime, end: datetime.datetime
    ) -> None:
        for parsed_line in self.parsed_lines:
            clock = parsed_line.clock
            if clock is None:
                continue

            clock.bound_time_range(start=start, end=end)

    def end_first_clock(
        self, *, now: Union[None, datetime.datetime] = None
    ) -> Union[None, ParsedLine]:
        if now is None:
            now = get_now()

        for parsed_line in self.parsed_lines:
            clock = parsed_line.clock
            if clock is None:
                continue

            end = clock.end
            if end is not None:
                continue

            clock.end = now
            return parsed_line

        return None

    def get_fix_clocks_diff(self) -> List[Tuple[int, str]]:
        fixes = []  # type: list[tuple[int, str]]

        last_level = 0
        for parsed_line in self.parsed_lines:
            headline = parsed_line.headline
            if headline is not None:
                last_level = headline.level

            clock = parsed_line.clock
            if clock is None:
                continue

            new_clock_line = clock.to_string()
            fixes.append(
                (parsed_line.line_number, "#" * last_level + " " + new_clock_line)
            )

        return fixes

    def get_started_clocks(self) -> Iterator[ParsedLine]:
        for parsed_line in self.parsed_lines:
            clock = parsed_line.clock
            if clock is None:
                continue

            if clock.end is not None:
                continue

            yield parsed_line

    def get_stopped_clocks(self) -> Iterator[ParsedLine]:
        for parsed_line in self.parsed_lines:
            clock = parsed_line.clock
            if clock is None:
                continue

            clock_end = clock.end
            if clock_end is None:
                continue

            yield parsed_line

    @classmethod
    def parse(cls, lines: Iterator[str]) -> "typing.Self":
        self = cls()

        is_inside_code_block = False
        parsed_lines = self.parsed_lines
        for line_number, line in enumerate(lines, start=1):
            parsed_line = ParsedLine(
                line=line,
                line_number=line_number,
            )
            parsed_lines.append(parsed_line)

            if is_inside_code_block:
                if line == "```":
                    is_inside_code_block = False
                continue
            if line.startswith("```"):
                is_inside_code_block = True
                continue

            parsed_line.reparse_line()

        return self

    def refresh_durations(self) -> None:
        # Level zero is root.
        child_level_durations = [datetime.timedelta()]
        for parsed_line in reversed(self.parsed_lines):
            headline = parsed_line.headline
            if not headline:
                continue

            duration = datetime.timedelta()

            clock = parsed_line.clock
            if clock is not None:
                duration = clock.get_duration()

            level = headline.level
            duration = parsed_line.duration = sum(
                child_level_durations[level + 1 :], duration
            )

            missing_levels = level + 1 - len(child_level_durations)
            if missing_levels > 0:
                child_level_durations += [datetime.timedelta()] * missing_levels
            else:
                child_level_durations = child_level_durations[: level + 1]
            child_level_durations[level] += duration

        self.duration = sum(child_level_durations, datetime.timedelta())

    def start_clock(self, *, line_number: int, now: datetime.datetime) -> ParsedLine:
        # Does not add to the document.
        for parsed_line in reversed(self.parsed_lines[:line_number]):
            if parsed_line.clock is not None:
                continue

            headline = parsed_line.headline
            if not headline:
                continue

            new_line_number = parsed_line.line_number + 1
            new_clock_level = headline.level + 1
            break
        else:
            new_clock_level = 1
            new_line_number = 1

        return ParsedLine(
            clock=Clock(start=now),
            headline=Headline(level=new_clock_level),
            line="",
            line_number=new_line_number,
        )


class QuicklistItem:
    def __init__(
        self, *args: typing.Any, lnum: int, text: str, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.lnum = lnum
        self.text = text


def get_summary_quicklist(
    parsed_document: ParsedDocument,
) -> List[QuicklistItem]:

    hour = datetime.timedelta(hours=1)

    quicklist = [
        QuicklistItem(lnum=1, text="| Duration / h | Headline"),
        QuicklistItem(
            lnum=1,
            text="| {hour_count:>12.2f} | {title}".format(
                hour_count=parsed_document.duration / hour, title="Total"
            ),
        ),
    ]

    for parsed_line in parsed_document.parsed_lines:
        duration = parsed_line.duration
        if not duration:
            continue

        headline = parsed_line.headline
        if not headline:
            continue

        title = headline.title
        if not title:
            title = parsed_line.line

        title = parsed_line.to_string()
        hour_count = duration / hour
        quicklist.append(
            QuicklistItem(
                lnum=parsed_line.line_number,
                text="| {hour_count:>12.2f} | {title}".format(
                    hour_count=hour_count, title=title
                ),
            )
        )

    return quicklist


class ParsedProject:
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self.duration = datetime.timedelta()
        self.parsed_documents = {}  # type: dict[pathlib.Path, ParsedDocument]

    @classmethod
    def parse(cls, paths: List[pathlib.Path]) -> "typing.Self":
        self = cls()

        parsed_documents = self.parsed_documents
        for path in paths:
            file_text = path.read_text(encoding="utf-8")
            parsed_document = ParsedDocument.parse(file_text.splitlines())
            parsed_documents[path] = parsed_document

        return self
