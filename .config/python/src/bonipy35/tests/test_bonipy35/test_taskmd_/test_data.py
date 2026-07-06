#!/usr/bin/env python3

# Standard libraries.
import datetime
import pathlib

# External dependencies.
import pytest

# Internal modules.
from bonipy35.taskmd_.data import Clock, Headline, Project


class TestHeadline:
    def test_parse_full(self) -> None:
        line = "### TODO [#A] COMMENT title :tag:"
        headline = Headline.parse(line)
        assert headline
        assert headline.comment
        assert headline.keyword == "TODO"
        assert headline.level == 3
        assert headline.priority == "A"
        assert headline.tags == ["tag"]
        assert headline.title == "title"

    def test_parse_blank_tag_part_is_not_tag(self) -> None:
        line = "### title :::"
        headline = Headline.parse(line)
        assert headline
        assert headline.tags is None
        assert headline.title == "title :::"

    def test_parse_blank_tags_is_not_tag(self) -> None:
        line = "### title ::"
        headline = Headline.parse(line)
        assert headline
        assert headline.tags is None
        assert headline.title == "title ::"

    @pytest.mark.parametrize(
        "line",
        (
            "# ",
            "#",
            "### TODO [#A] COMMENT title :tag: ",
            "### TODO [#A] COMMENT title :tag:",
            "### title ::",
            "### title :::",
        ),
    )
    def test_parse_stable(self, line: str) -> None:
        headline = Headline.parse(line)
        assert headline
        as_string = headline.to_string()
        assert as_string
        assert as_string == line

    def test_parse_tag_must_end_line(self) -> None:
        line = "### TODO [#A] COMMENT title :tag: "
        headline = Headline.parse(line)
        assert headline
        assert headline.comment
        assert headline.keyword == "TODO"
        assert headline.level == 3
        assert headline.priority == "A"
        assert headline.tags is None
        assert headline.title == "title :tag: "

    def test_to_string(self) -> None:
        headline = Headline(
            comment=True,
            keyword="TODO",
            level=3,
            priority="A",
            tags=["tag"],
            title="title",
        )
        as_string = headline.to_string()
        assert as_string == "### TODO [#A] COMMENT title :tag:"

    def test_to_string_default_is_hash(self) -> None:
        headline = Headline(level=1)
        as_string = headline.to_string()
        assert as_string == "#"


class TestClock:
    def test_get_duration(self) -> None:
        clock = Clock(
            start=datetime.datetime(1970, 1, 2),
            end=datetime.datetime(1970, 1, 4),
        )
        duration = clock.get_duration()
        assert duration == datetime.timedelta(hours=48)

    def test_to_string(self) -> None:
        clock = Clock(start=datetime.datetime(1970, 1, 2))
        as_string = clock.to_string()
        assert as_string == "CLOCK: (1970-01-02T00:00:00)"

    def test_to_string_with_end(self) -> None:
        clock = Clock(
            start=datetime.datetime(1970, 1, 2),
            end=datetime.datetime(1970, 1, 3),
        )
        as_string = clock.to_string()
        assert as_string == (
            "CLOCK: (1970-01-02T00:00:00)--(1970-01-03T00:00:00) => 1 day, 0:00:00"
        )

    def test_to_string_with_timezone(self) -> None:
        clock = Clock(
            start=datetime.datetime(
                1970,
                1,
                2,
                tzinfo=datetime.timezone.utc,
            ),
        )
        as_string = clock.to_string()
        assert as_string == "CLOCK: (1970-01-02T00:00:00+0000)"


class TestProject:
    def test_empty_project(self) -> None:
        project = Project()
        assert project.duration == datetime.timedelta()
        assert not project.parsed_documents

    def test_parse(
        self, input_path: pathlib.Path, reference_path: pathlib.Path
    ) -> None:
        Project.parse(list(input_path.glob("*.task.md")))
        reference_path.parent.mkdir(exist_ok=True, parents=True)
        reference_path.touch(mode=0o644)
