#!/usr/bin/env python3

# Standard libraries.
import inspect
import io
import pathlib

# External dependencies.
import pytest

# Internal modules.
from bonipy38.taskmd import run, to_clock, to_headline


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


class TestToClock:
    def test_counts_level_by_heading(self) -> None:
        line = "CLOCK: [2024-11-12T00:00:00+00:00]--[2025-11-12T00:00:00+00:00]"
        clock = to_clock(line)
        assert clock is not None

        line = "CLOCK: [2024-11-12T00:00:00+00:00]--[2025-11-12T00:00:00+00:00]"
        clock = to_clock(line)
        assert clock is not None

        line = "CLOCK: [2024-11-12T00:00:00+00:00]--[2025-11-12T00:00:00+00:00]"
        clock = to_clock(line)
        assert clock is not None

        line = "CLOCK: [2024-11-12T00:00:00+00:00]--[2025-11-12T00:00:00+00:00]"
        clock = to_clock(line)
        assert clock is not None

        line = "CLOCK: [2024-11-12T00:00:00+00:00]--[2025-11-12T00:00:00+00:00]"
        clock = to_clock(line)
        assert clock is not None

        line = "CLOCK: [2024-11-12T00:00:00+00:00]--[2025-11-12T00:00:00+00:00]"
        clock = to_clock(line)
        assert clock is not None

    def test_ignore_duration_suffix(self) -> None:
        line = (
            "CLOCK: [2024-11-12T00:00:00+00:00]--[2025-11-12T00:01:00+00:00] => 01:00"
        )
        clock = to_clock(line)
        assert clock is not None

    def test_no_end(self) -> None:
        line = "CLOCK: [2024-11-12T00:00:00+00:00]"
        clock = to_clock(line)
        assert clock is not None
        assert "end" not in clock


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
