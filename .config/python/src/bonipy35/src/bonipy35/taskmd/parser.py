#!/usr/bin/env python3

# Need Python 3.5 support.
# pylint: disable=consider-using-f-string

# Standard libraries.
import datetime
import pathlib
import re
import time
import typing

from typing import List, Tuple, Union

# Internal modules.
from . import errors
from . import model


class BodyLineToken:
    """A single non-heading line."""

    def __init__(
        self,
        *args: typing.Any,
        line_number: int,
        text: str,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.line_number = line_number
        self.text = text


Frame = typing.NamedTuple(
    "Frame",
    [("depth", int), ("task", model.Task)],
)


class HeadingToken:
    """A single Markdown heading line."""

    def __init__(
        self,
        *args: typing.Any,
        depth: int,
        line_number: int,
        text: str,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.depth = depth
        self.line_number = line_number
        self.text = text


Token = Union[BodyLineToken, HeadingToken]


class ParseConfig:
    def __init__(  # pylint: disable=too-many-arguments
        self,
        *args: typing.Any,
        datetime_formats: Union[None, List[str]] = None,
        local_timezone: Union[None, datetime.tzinfo] = None,
        require_timezone: Union[None, bool] = None,
        strict: Union[None, bool] = None,
        warn_open_clocks: Union[None, bool] = None,
        warnings: Union[None, List[errors.ParseWarning]] = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        if datetime_formats is None:
            # No `%z` here.
            # These formats only need to match the timezone-naive part.
            # Any timezone offset is split off and parsed separately
            # due to incomplete timezone support in Python 3.5.
            datetime_formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M",
            ]
        if local_timezone is None:
            local_timezone = get_local_timezone()
        if strict is None:
            strict = True
        if warnings is None:
            warnings = []
        if require_timezone is None:
            require_timezone = strict
        if warn_open_clocks is None:
            warn_open_clocks = strict

        self.datetime_formats = datetime_formats
        self.local_timezone = local_timezone
        self.require_timezone = require_timezone
        self.strict = strict
        self.warn_open_clocks = warn_open_clocks
        self.warnings = warnings

    def collected_warnings(self) -> List[errors.ParseWarning]:
        return list(self.warnings)

    def record_warning(self, warning: errors.ParseWarning) -> None:
        self.warnings.append(warning)


def build_tree(  # pylint: disable=too-many-locals
    tokens: List[Token],
    *,
    config: ParseConfig,
    path: Union[None, pathlib.Path] = None
) -> model.TaskFile:
    task_file = model.TaskFile(path=path)

    stack = []  # type: List[Frame]

    accumulator_target = (
        None
    )  # type: Union[None, model.ClockEntry, model.Task, model.Update]
    accumulator_lines = []  # type: List[str]

    for token in tokens:
        if isinstance(token, BodyLineToken):
            accumulator_lines.append(token.text)
            continue

        set_text(accumulator_target, accumulator_lines)
        accumulator_lines.clear()
        accumulator_target = None

        depth = token.depth
        text = token.text
        line_number = token.line_number

        while stack and stack[-1].depth >= depth:
            stack.pop()

        if matches_status(text, config=config):
            status, title, tags = parse_status_heading(
                text, config=config, line_number=line_number
            )
            task = model.Task(
                level=depth,
                status=status,
                title=title,
                tags=tags,
                source_line=line_number,
            )
            if not stack:
                task_file.tasks.append(task)
            else:
                stack[-1].task.tasks.append(task)
            stack.append(Frame(depth, task))
            accumulator_target = task
            continue

        if not stack:
            # A CLOCK:/update-shaped heading with no enclosing task.
            message = (
                "heading {0!r} at line {1} has no enclosing task".format(
                    text,
                    line_number,
                )
            )
            if config.strict:
                raise errors.UnknownHeadingError(message, line_number)
            config.record_warning(errors.ParseWarning(message, line_number))
            continue

        parent_task = stack[-1].task

        if text.startswith("CLOCK:"):
            start, end, description = parse_clock_heading(
                text,
                config=config,
                line_number=line_number,
            )
            if start is None:
                continue
            clock = model.ClockEntry(
                start=start,
                end=end,
                description=description,
                work_notes="",
                source_line=line_number,
            )
            parent_task.clocks.append(clock)
            accumulator_target = clock
            continue

        timestamp, title = parse_update_heading(
            text, config=config, line_number=line_number
        )
        update = model.Update(
            timestamp=timestamp,
            title=title,
            body="",
            source_line=line_number,
        )
        parent_task.updates.append(update)
        accumulator_target = update

    set_text(accumulator_target, accumulator_lines)

    task_file.warnings = config.collected_warnings()

    check_open_clocks(task_file, config=config)

    return task_file


def check_open_clocks(
    task_file: model.TaskFile, *, config: ParseConfig
) -> None:
    if not config.warn_open_clocks:
        return

    for task in task_file.walk():
        for clock in task.clocks:
            if not clock.is_open():
                continue
            config.record_warning(
                errors.ParseWarning(
                    "task {0!r} has an unclosed CLOCK: entry starting "
                    "at line {1}".format(task.title, clock.source_line),
                    clock.source_line,
                ),
            )

    task_file.warnings = config.collected_warnings()


def extract_tags(text: str) -> Tuple[str, List[str]]:
    tag_block_re = re.compile(r"(?:\s*)(:[a-z0-9_-]+(?::[a-z0-9_-]+)*:)\s*$")

    match = tag_block_re.search(text)
    if not match:
        return text, []
    tag_block = match.group(1)
    tags = [tag for tag in tag_block.split(":") if tag]
    remaining = text[: match.start()].rstrip()
    return remaining, tags


def get_local_timezone() -> datetime.timezone:
    """Return the system's local UTC offset as a `datetime.timezone`.

    Written by hand instead of `datetime.now().astimezone().tzinfo`
    because naive `astimezone()` (with no argument) was only added in
    Python 3.6; this needs to work on Python 3.5. `time.timezone` /
    `time.altzone` and `datetime.timezone` are both available back to
    Python 3.2, so this works everywhere `taskmd` claims to support.
    """
    if time.daylight and time.localtime().tm_isdst:
        offset_seconds = -time.altzone
    else:
        offset_seconds = -time.timezone
    return datetime.timezone(datetime.timedelta(seconds=offset_seconds))


STATUS_KEYWORDS = ("TODO", "DONE", "DROP", "WAIT")
STATUS_HEADING_RE = re.compile(
    r"^({0})(?:\s+(.*))?$".format("|".join(STATUS_KEYWORDS)),
)


def matches_status(text: str, *, config: ParseConfig) -> bool:
    if config.strict:
        return bool(STATUS_HEADING_RE.match(text))
    return bool(STATUS_HEADING_RE.match(text.upper()))


def parse_clock_heading(
    text: str, *, config: ParseConfig, line_number: int
) -> Union[
    Tuple[None, None, str],
    Tuple[datetime.datetime, None, str],
    Tuple[datetime.datetime, datetime.datetime, str],
]:

    clock_fallback_re = re.compile(r"\[(?P<start>[^\]]+)\]\s*(?P<rest>.*)$")
    clock_heading_re = re.compile(
        r"^CLOCK:\s*\[(?P<start>[^\]]*)\]"
        r"--(?:\[(?P<end>[^\]]*)\])?"
        r"\s*(?P<description>.*)$",
    )

    match = clock_heading_re.match(text)
    if not match:
        if config.strict:
            raise errors.ClockFormatError(
                "malformed CLOCK heading: {0!r}".format(text),
                line_number,
            )

        fallback = clock_fallback_re.search(text)
        if not fallback:
            config.record_warning(
                errors.ParseWarning(
                    "malformed CLOCK heading, no recoverable datetime: "
                    "{0!r}".format(text),
                    line_number,
                ),
            )
            return None, None, text
        config.record_warning(
            errors.ParseWarning(
                "malformed CLOCK heading (missing '--'), best-effort "
                "parsed as an open session: {0!r}".format(text),
                line_number,
            ),
        )
        start = parse_datetime(
            fallback.group("start"), config=config, line_number=line_number
        )
        description = fallback.group("rest").strip()
        return start, None, description
    start = parse_datetime(
        match.group("start"), config=config, line_number=line_number
    )
    end_raw = match.group("end")
    end = (
        parse_datetime(end_raw, config=config, line_number=line_number)
        if end_raw not in (None, "")
        else None
    )
    description = match.group("description").strip()
    return start, end, description


def parse_datetime(
    raw: str, *, config: "ParseConfig", line_number: int
) -> typing.Any:
    """Parse a single datetime string per the active `ParseConfig`.

    Raises `errors.TimezoneError` in strict mode if `raw` has no
    timezone offset. In lenient mode, a missing timezone is recorded
    as a warning on `config` (via `config.record_warning`, if set) and
    `config.local_timezone` (or the system local zone) is applied.
    """
    raw = raw.strip()
    naive_part, tzinfo_value = split_timezone_suffix(raw)

    parsed = None
    for fmt in config.datetime_formats:
        try:
            parsed = datetime.datetime.strptime(naive_part, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        raise errors.ClockFormatError(
            "could not parse datetime {0!r}".format(raw),
            line_number,
        )
    if tzinfo_value is not None:
        parsed = parsed.replace(tzinfo=tzinfo_value)

    if parsed.tzinfo is None:
        if config.strict:
            raise errors.TimezoneError(
                "datetime {0!r} is missing a required timezone offset".format(
                    raw
                ),
                line_number,
            )

        config.record_warning(
            errors.ParseWarning(
                "datetime {0!r} has no timezone offset; assuming local "
                "timezone".format(raw),
                line_number,
            ),
        )
        local_tz = config.local_timezone
        parsed = parsed.replace(tzinfo=local_tz)
    return parsed


def parse_file(
    path: pathlib.Path, *, config: Union[None, ParseConfig] = None
) -> model.TaskFile:
    path = pathlib.Path(path)
    text = path.read_text(encoding="utf-8")
    return parse_string(text, config=config, path=path)


def parse_status_heading(
    text: str, *, config: ParseConfig, line_number: int
) -> Tuple[model.Status, str, List[str]]:
    body, tags = extract_tags(text)
    match = STATUS_HEADING_RE.match(body if config.strict else body.upper())
    if not match:
        raise errors.StatusError(
            "heading {0!r} does not start with a status keyword".format(text),
            line_number,
        )
    status = model.Status[match.group(1)]
    # Recover the original-case title from `body`, not the upper-cased
    # copy used only for matching in lenient mode.
    title = body[match.end(1) :].strip()
    return status, title, tags


def parse_string(
    text: str,
    *,
    config: Union[None, ParseConfig] = None,
    path: Union[None, pathlib.Path] = None
) -> model.TaskFile:
    if config is None:
        config = ParseConfig()

    tokens = scan_lines(text)
    return build_tree(tokens, config=config, path=path)


def parse_update_heading(
    text: str, *, config: ParseConfig, line_number: int
) -> Union[
    Tuple[None, str],
    Tuple[datetime.datetime, str],
]:
    update_timestamp_re = re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?"
        r"(?:Z|[+-]\d{2}:?\d{2})?)"
        r"(?:\s+(?P<rest>.*))?$",
    )

    match = update_timestamp_re.match(text)
    if not match:
        return None, text
    timestamp = parse_datetime(
        match.group("timestamp"), config=config, line_number=line_number
    )
    title = match.group("rest") or ""
    return timestamp, title


def scan_lines(text: str) -> List[Token]:
    heading_regex = re.compile(r"^(#+)\s+(.*?)\s*$")

    tokens = []  # type: List[Token]
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        match = heading_regex.match(raw_line)
        if match:
            depth = len(match.group(1))
            heading_text = match.group(2)
            tokens.append(
                HeadingToken(
                    depth=depth, text=heading_text, line_number=line_number
                )
            )
        else:
            tokens.append(
                BodyLineToken(text=raw_line, line_number=line_number)
            )
    return tokens


def set_text(
    accumulator_target: Union[
        None, model.ClockEntry, model.Task, model.Update
    ],
    accumulator_lines: List[str],
) -> None:
    if accumulator_target is None or not accumulator_lines:
        return
    text = "\n".join(accumulator_lines).strip("\n")
    if isinstance(accumulator_target, model.Task):
        accumulator_target.description = text
    elif isinstance(accumulator_target, model.Update):
        accumulator_target.body = text
    elif isinstance(accumulator_target, model.ClockEntry):
        accumulator_target.work_notes = text


TZ_SUFFIX_RE = re.compile(r"(Z|[+-]\d{2}(?::?\d{2})?)$")


def split_timezone_suffix(
    raw: str,
) -> Tuple[str, Union[None, datetime.timezone]]:
    """Split a trailing timezone offset from an ISO datetime string.

    Returns `(naive_part, tzinfo_or_None)`.

    Recognizes a trailing `Z` (UTC) or a numeric offset (`+02:00`, `+0200`, or `+02`),
    with or without a colon.

    The `%z` directive for `datetime.strptime`
    gained support for colons and a literal `Z` suffix in Python 3.7.
    This function partially backports that for Python 3.5
    """
    match = TZ_SUFFIX_RE.search(raw)
    if not match:
        return raw, None
    suffix = match.group(1)
    naive_part = raw[: match.start()]
    if suffix == "Z":
        return naive_part, datetime.timezone.utc
    sign = 1 if suffix[0] == "+" else -1
    digits = suffix[1:].replace(":", "")
    hours = int(digits[:2])
    minutes = int(digits[2:]) if len(digits) > 2 else 0
    offset = sign * datetime.timedelta(hours=hours, minutes=minutes)
    return naive_part, datetime.timezone(offset)
