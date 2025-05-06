#!/usr/bin/env python3

# Standard libraries.
import datetime
import inspect
import io
import pathlib

# External dependencies.
import pytest

# Internal modules.
from bonipy38.taskmd import (
    Clock,
    Headline,
    ParsedLine,
    end_first_clock,
    get_parsed_line_durations,
    run,
    start_clock,
    to_clock,
    to_headline,
    to_parsed_lines,
    to_string_from_clock,
    to_string_from_headline,
    to_string_from_parsed_line,
)


def get_module_path() -> pathlib.Path:
    module_path_value = inspect.getsourcefile(lambda: None)
    if not module_path_value:
        raise RuntimeError("Unable to determine module path.")
    return pathlib.Path(module_path_value)


def get_input_paths() -> list[pathlib.Path]:
    module_path = get_module_path()
    module_directory = module_path.parent
    module_name = module_path.stem.removeprefix("test_")
    input_directory = module_directory / ("input_" + module_name)
    return sorted(input_path for input_path in input_directory.iterdir())


@pytest.fixture(
    ids=lambda path: path.name,
    name="input_path",
    params=get_input_paths(),
    scope="package",
)
def fixture_input_path(request: pytest.FixtureRequest) -> pathlib.Path:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture(name="reference_path")
def fixture_reference_path(
    input_path: pathlib.Path, request: pytest.FixtureRequest
) -> pathlib.Path:
    module_path = get_module_path()
    module_directory = module_path.parent
    module_name = module_path.stem.removeprefix("test_")
    test_name = request.node.originalname  # type: str
    reference_directory = module_directory / ("reference_" + module_name) / test_name
    reference_directory.mkdir(exist_ok=True, parents=True)
    return reference_directory / (input_path.name + ".txt")


class TestToHeadline:
    def test_empty(self) -> None:
        headline = to_headline("")
        assert headline is None

    def test_ignore_headline_without_space(self) -> None:
        line = "##"
        headline = to_headline(line)
        assert headline is None

    def test_parses_keyword(self) -> None:
        line = "# DONE"
        headline = to_headline(line)
        assert headline is not None
        assert headline["keyword"] == "DONE"

        line = "# TODO"
        headline = to_headline(line)
        assert headline is not None
        assert headline["keyword"] == "TODO"

        line = "# TODO [#A]"
        headline = to_headline(line)
        assert headline is not None
        assert headline["keyword"] == "TODO"

    def test_parses_level(self) -> None:
        line = "# Level 1"
        headline = to_headline(line)
        assert headline is not None
        assert headline["level"] == 1

        line = "## Level 2"
        headline = to_headline(line)
        assert headline is not None
        assert headline["level"] == 2

        line = "### Level 3"
        headline = to_headline(line)
        assert headline is not None
        assert headline["level"] == 3

        line = "#### Level 4"
        headline = to_headline(line)
        assert headline is not None
        assert headline["level"] == 4

        line = "##### Level 5"
        headline = to_headline(line)
        assert headline is not None
        assert headline["level"] == 5

        line = "###### Level 6"
        headline = to_headline(line)
        assert headline is not None
        assert headline["level"] == 6

    def test_parses_level_keyword_priority_comment_title_tags(self) -> None:
        line = "## TODO [#B] COMMENT abc :tag1@abc:tag2:"
        headline = to_headline(line)
        assert headline is not None
        assert headline["level"] == 2
        assert headline["keyword"] == "TODO"
        assert headline["priority"] == "B"
        assert headline["comment"]
        assert headline["title"] == "abc"
        assert headline["tags"] == ["tag1@abc", "tag2"]

    def test_parses_priority(self) -> None:
        line = "# [#Z]"
        headline = to_headline(line)
        assert headline is not None
        assert headline["priority"] == "Z"

        line = "# TODO [#A]"
        headline = to_headline(line)
        assert headline is not None
        assert headline["priority"] == "A"

        line = "# [#B] COMMENT"
        headline = to_headline(line)
        assert headline is not None
        assert headline["priority"] == "B"


class TestToStringFromHeadline:
    def test_comment_only(self) -> None:
        headline = {"level": 5, "comment": True}  # type: Headline
        as_string = to_string_from_headline(headline)
        assert as_string == "##### COMMENT"

    def test_keyword_only(self) -> None:
        headline = {"level": 1, "keyword": "TODO"}  # type: Headline
        as_string = to_string_from_headline(headline)
        assert as_string == "# TODO"

    def test_level_only(self) -> None:
        headline = {"level": 2}  # type: Headline
        as_string = to_string_from_headline(headline)
        assert as_string == "## "

    def test_priority_only(self) -> None:
        headline = {"level": 3, "priority": "C"}  # type: Headline
        as_string = to_string_from_headline(headline)
        assert as_string == "### [#C]"

    def test_tags_empty(self) -> None:
        headline = {"level": 6, "tags": [""]}  # type: Headline
        as_string = to_string_from_headline(headline)
        assert as_string == "###### "

    def test_tags_only(self) -> None:
        headline = {"level": 2, "tags": ["tag1", "tag2"]}  # type: Headline
        as_string = to_string_from_headline(headline)
        assert as_string == "## :tag1:tag2:"

    def test_title_only(self) -> None:
        headline = {"level": 4, "title": "This is a Title"}  # type: Headline
        as_string = to_string_from_headline(headline)
        assert as_string == "#### This is a Title"


class TestToClock:
    def test_start_with_end(self) -> None:
        line = "CLOCK: (2024-11-12T00:00:00+00:00)--(2025-11-12T00:00:00+00:00)"
        clock = to_clock(line)
        expected_clock = {
            "start": datetime.datetime(2024, 11, 12, tzinfo=datetime.timezone.utc),
            "end": datetime.datetime(2025, 11, 12, 0, 0, tzinfo=datetime.timezone.utc),
        }
        assert clock is not None
        assert clock == expected_clock

    def test_ignore_duration_suffix(self) -> None:
        line = (
            "CLOCK: (2024-11-12T00:00:00+00:00)--(2025-11-12T00:01:00+00:00) => 01:00"
        )
        clock = to_clock(line)
        expected_clock = {
            "start": datetime.datetime(2024, 11, 12, tzinfo=datetime.timezone.utc),
            "end": datetime.datetime(2025, 11, 12, 0, 1, tzinfo=datetime.timezone.utc),
        }
        assert clock is not None
        assert clock == expected_clock

    def test_no_end(self) -> None:
        line = "CLOCK: (2024-11-12T00:00:00+00:00)"
        clock = to_clock(line)
        expected_clock = {
            "start": datetime.datetime(2024, 11, 12, tzinfo=datetime.timezone.utc),
        }
        assert clock is not None
        assert clock == expected_clock


class TestToStringFromClock:
    def test_start_only(self) -> None:
        clock = {"start": datetime.datetime(2000, 1, 1)}  # type: Clock
        as_string = to_string_from_clock(clock)
        assert as_string == "CLOCK: (2000-01-01T00:00:00)"

    def test_start_with_end(self) -> None:
        clock = {
            "start": datetime.datetime(2000, 1, 1),
            "end": datetime.datetime(2000, 1, 1, 1, 2, 0),
        }  # type: Clock
        as_string = to_string_from_clock(clock)
        assert (
            as_string
            == "CLOCK: (2000-01-01T00:00:00)--(2000-01-01T01:02:00) => 1:02:00"
        )


class TestToStringFromParsedLine:
    def test_clock_ignores_content(self) -> None:
        parsed_line = {
            "line_number": 1,
            "content": "This is ignored.",
            "clock": {"start": datetime.datetime(2000, 1, 1)},
        }  # type: ParsedLine
        as_string = to_string_from_parsed_line(parsed_line)
        assert as_string == "# CLOCK: (2000-01-01T00:00:00)"

    def test_clock_ignores_headline_title(self) -> None:
        parsed_line = {
            "line_number": 1,
            "content": "This is ignored.",
            "headline": {
                "level": 1,
                "title": "This is also ignored.",
            },
            "clock": {"start": datetime.datetime(2000, 1, 1)},
        }  # type: ParsedLine
        as_string = to_string_from_parsed_line(parsed_line)
        assert as_string == "# CLOCK: (2000-01-01T00:00:00)"

    def test_content_is_default(self) -> None:
        parsed_line = {
            "line_number": 3,
            "content": "Content is used.",
        }  # type: ParsedLine
        as_string = to_string_from_parsed_line(parsed_line)
        assert as_string == "Content is used."

    def test_headline_ignores_content(self) -> None:
        parsed_line = {
            "line_number": 2,
            "content": "Content is ignored.",
            "headline": {
                "level": 2,
                "title": "This is Part of Actual Content",
            },
        }  # type: ParsedLine
        as_string = to_string_from_parsed_line(parsed_line)
        assert as_string == "## This is Part of Actual Content"


class TestParse:
    def test_no_headlines(self) -> None:
        lines = ["These", "are not", "headlines."]  # type: list[str]
        parsed_lines = to_parsed_lines(lines)
        expected_parsed_lines = [
            {"line_number": 1, "content": "These"},
            {"line_number": 2, "content": "are not"},
            {"line_number": 3, "content": "headlines."},
        ]
        assert parsed_lines == expected_parsed_lines

    def test_no_lines(self) -> None:
        lines = []  # type: list[str]
        parsed_lines = to_parsed_lines(lines)
        assert not parsed_lines

    def test_one_clock(self) -> None:
        lines = ["# CLOCK: (2000-09-09T00:00:00+00:00)"]  # type: list[str]
        parsed_lines = to_parsed_lines(lines)
        expected_parsed_lines = [
            {
                "line_number": 1,
                "content": "# CLOCK: (2000-09-09T00:00:00+00:00)",
                "headline": {"level": 1, "title": "CLOCK: (2000-09-09T00:00:00+00:00)"},
                "clock": {
                    "start": datetime.datetime(2000, 9, 9, tzinfo=datetime.timezone.utc)
                },
            },
        ]
        assert parsed_lines == expected_parsed_lines

    def test_one_headline(self) -> None:
        lines = ["# This is a Headline"]  # type: list[str]
        parsed_lines = to_parsed_lines(lines)
        expected_parsed_lines = [
            {
                "line_number": 1,
                "content": "# This is a Headline",
                "headline": {"level": 1, "title": "This is a Headline"},
            },
        ]
        assert parsed_lines == expected_parsed_lines


class TestEndFirstClock:
    def test_ends_first_clock_only(self) -> None:
        parsed_lines = [
            {
                "line_number": 1,
                "content": "# CLOCK: (2000-09-09T00:00:00+00:00)",
                "headline": {"level": 1, "title": "CLOCK: (2000-09-09T00:00:00+00:00)"},
                "clock": {
                    "start": datetime.datetime(2000, 9, 9, tzinfo=datetime.timezone.utc)
                },
            },
        ]  # type: list[ParsedLine]
        new_parsed_line = end_first_clock(
            parsed_lines, now=datetime.datetime(2000, 9, 9, 1)
        )
        expected_parsed_line = {
            "line_number": 1,
            "content": "# CLOCK: (2000-09-09T00:00:00+00:00)",
            "headline": {"level": 1, "title": "CLOCK: (2000-09-09T00:00:00+00:00)"},
            "clock": {
                "start": datetime.datetime(2000, 9, 9, tzinfo=datetime.timezone.utc),
                "end": datetime.datetime(2000, 9, 9, 1),
            },
        }
        assert new_parsed_line == expected_parsed_line

    def test_no_clocks(self) -> None:
        parsed_lines = [
            {
                "line_number": 1,
                "content": "This is",
            },
            {
                "line_number": 2,
                "content": "# Not a clock",
                "headline": {"level": 1, "title": "Not a clock"},
            },
        ]  # type: list[ParsedLine]
        new_parsed_line = end_first_clock(
            parsed_lines, now=datetime.datetime(2000, 9, 9, 1)
        )
        assert new_parsed_line is None

    def test_no_lines(self) -> None:
        parsed_lines = []  # type: list[ParsedLine]
        new_parsed_line = end_first_clock(
            parsed_lines, now=datetime.datetime(2000, 9, 9, 1)
        )
        assert new_parsed_line is None

    def test_no_started_clocks(self) -> None:
        parsed_lines = [
            {
                "line_number": 1,
                "content": "# CLOCK: (2000-09-09T00:00:00+00:00)--(2000-09-09T00:00:00+00:00)",
                "headline": {
                    "level": 1,
                    "title": "CLOCK: (2000-09-09T00:00:00+00:00)--(2000-09-09T00:00:00+00:00)",
                },
                "clock": {
                    "start": datetime.datetime(
                        2000, 9, 9, tzinfo=datetime.timezone.utc
                    ),
                    "end": datetime.datetime(2000, 9, 9, tzinfo=datetime.timezone.utc),
                },
            }
        ]  # type: list[ParsedLine]
        new_parsed_line = end_first_clock(
            parsed_lines, now=datetime.datetime(2000, 9, 9, 1)
        )
        assert new_parsed_line is None


class TestStartClock:
    def test_append_after_last_headline(self) -> None:
        parsed_lines = [
            {
                "line_number": 1,
                "content": "",
                "headline": {
                    "level": 2,
                },
            },
            {
                "line_number": 2,
                "content": "",
                "headline": {
                    "level": 3,
                },
            },
            {
                "line_number": 3,
                "content": "",
            },
        ]  # type: list[ParsedLine]
        now = datetime.datetime(2000, 1, 1)
        append_line = start_clock(parsed_lines, now=now)
        assert append_line["line_number"] == 3

    def test_ignores_clocks(self) -> None:
        parsed_lines = [
            {
                "line_number": 1,
                "content": "",
                "headline": {
                    "level": 2,
                },
                "clock": {
                    "start": datetime.datetime(2000, 1, 1),
                },
            },
        ]  # type: list[ParsedLine]
        now = datetime.datetime(2000, 1, 1)
        append_line = start_clock(parsed_lines, now=now)
        assert append_line["line_number"] == 1

    def test_insert_as_first_line_if_no_headlines(self) -> None:
        parsed_lines = [
            {
                "line_number": 1,
                "content": "",
            },
            {
                "line_number": 2,
                "content": "",
            },
        ]  # type: list[ParsedLine]
        now = datetime.datetime(2000, 1, 1)
        append_line = start_clock(parsed_lines, now=now)
        assert append_line["line_number"] == 1

    def test_insert_as_first_line_if_no_lines(self) -> None:
        now = datetime.datetime(2000, 1, 1)
        append_line = start_clock([], now=now)
        assert append_line["line_number"] == 1


class TestGetParsedLineDurations:
    def test_no_lines(self) -> None:
        parsed_line_durations = get_parsed_line_durations([])
        assert not parsed_line_durations


def test_run(input_path: pathlib.Path, reference_path: pathlib.Path) -> None:
    stdout = io.StringIO()
    with input_path.open() as stdin:
        assert run(stdin=stdin, stdout=stdout) == 0

    try:
        reference = reference_path.read_text()
    except FileNotFoundError:
        reference_path.write_text(stdout.getvalue())
    else:
        assert stdout.getvalue() == reference
