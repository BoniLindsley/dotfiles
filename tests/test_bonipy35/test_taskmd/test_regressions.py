#!/usr/bin/env python3

# Standard libraries.
import datetime
import os
import pathlib
import subprocess
import sys

# External dependencies.
import pytest

# Internal modules.
from bonipy35.taskmd.clock import (
    LineRewriter,
    clock_start,
    clock_stop,
    find_task_at_line,
)
from bonipy35.datetime_ext import Builder
from bonipy35.taskmd.model import Status
from bonipy35.taskmd.parser import ParseConfig, parse_file, parse_string
from bonipy35.taskmd.recur import expand, parse_rule
from bonipy35.taskmd.errors import RecurParseError
from bonipy35.taskmd.report import Filter, aggregate, grand_total
from bonipy35.taskmd.vim import (
    Runner,
    schedule_show,
    schedule_conflicts,
    schedule_summary,
)


class TestClockStart:
    def test_body_lines_remain_description(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = tmp_path / "notes.task.md"
        path.write_bytes(b"# TODO A\r\nfirst\nlast")
        parsed = parse_file(path)
        assert parsed.total_lines == 3
        assert find_task_at_line(parsed, 3) is parsed.tasks[0]
        clock_start(path, line=3)
        assert path.read_bytes().startswith(
            b"# TODO A\r\nfirst\nlast\r\n## CLOCK:"
        )
        assert parse_file(path).tasks[0].description == "first\nlast"

    def test_sibling_event_ends_task(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "notes.task.md"
        event = "# EVENT [2025-06-01T10:00Z--2025-06-01T11:00Z] E\n"
        path.write_text("# TODO A\n" + event)
        assert find_task_at_line(parse_file(path), 2) is None
        clock_start(path, line=1)
        parsed = parse_file(path)
        assert len(parsed.tasks[0].clocks) == 1
        assert not parsed.events[0].clocks
        clock_stop(path)
        assert path.read_text().endswith(event)


class TestClockStop:
    def test_preserves_unaffected_bytes(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "notes.task.md"
        path.write_bytes(
            b"# TODO A\r\n## CLOCK: [2025-06-01T09:00Z]--\r\nnotes\nlast"
        )
        at = datetime.datetime(2025, 6, 1, 10, tzinfo=datetime.timezone.utc)
        clock_stop(path, at=at)
        assert path.read_bytes() == (
            b"# TODO A\r\n## CLOCK: [2025-06-01T09:00:00+00:00]--"
            b"[2025-06-01T10:00:00+00:00]\r\nnotes\nlast"
        )


class TestAggregate:
    def test_context_parent_has_no_own_time(self) -> None:
        parsed = parse_string(
            "# DONE parent\n"
            "## CLOCK: [2025-06-01T09:00Z]--[2025-06-01T10:00Z]\n"
            "## TODO child\n"
            "### CLOCK: [2025-06-01T09:00Z]--[2025-06-01T10:00Z]\n"
        )
        nodes = aggregate(parsed, Filter(statuses=[Status.TODO]))
        assert nodes[0].own_duration == datetime.timedelta(0)
        assert grand_total(nodes) == datetime.timedelta(hours=1)

    def test_event_clocks_obey_date_filter_without_mutating_input(
        self,
    ) -> None:
        parsed = parse_string(
            "# TODO A\n"
            "## EVENT [2025-01-01T09:00Z--2025-01-01T10:00Z] E\n"
            "### CLOCK: [2025-01-01T09:00Z]--[2025-01-01T10:00Z]\n"
            "### EVENT [2025-06-01T09:00Z--2025-06-01T10:00Z] S\n"
            "#### CLOCK: [2025-06-01T09:00Z]--[2025-06-01T10:00Z]\n"
        )
        nodes = aggregate(parsed, Filter(from_date=datetime.date(2025, 6, 1)))
        assert grand_total(nodes) == datetime.timedelta(hours=1)
        assert grand_total(aggregate(parsed)) == datetime.timedelta(hours=2)


class TestParseRule:
    @pytest.mark.parametrize("raw", ["+1m 0MON", "+1w @2025-02-30"])
    def test_invalid_rules_raise_parse_error(self, raw: str) -> None:
        with pytest.raises(RecurParseError) as caught:
            parse_rule(raw, line_number=7)
        assert caught.value.line_number == 7
        parsed = parse_string(
            "# EVENT [2025-01-01T09:00Z--2025-01-01T10:00Z] E RECUR " + raw,
            config=ParseConfig(strict=False),
        )
        assert parsed.warnings


class TestExpand:
    @pytest.mark.parametrize(
        "raw,anchor,expected",
        [
            ("+1m", "2024-01-31", ["2024-01-31", "2024-03-31"]),
            ("+2m", "2024-01-31", ["2024-01-31", "2024-03-31"]),
            ("+1y", "2024-02-29", ["2024-02-29"]),
            ("+1m 5MON", "2024-01-01", ["2024-01-29"]),
            ("+1m -5MON", "2024-01-01", ["2024-01-01"]),
            (
                "+2w MON,WED",
                "2024-01-03",
                [
                    "2024-01-03",
                    "2024-01-15",
                    "2024-01-17",
                    "2024-01-29",
                    "2024-01-31",
                    "2024-02-12",
                    "2024-02-14",
                    "2024-02-26",
                    "2024-02-28",
                    "2024-03-11",
                    "2024-03-13",
                    "2024-03-25",
                    "2024-03-27",
                ],
            ),
        ],
    )
    def test_calendar_boundaries(
        self, raw: str, anchor: str, expected: list[str]
    ) -> None:
        start = datetime.datetime.strptime(anchor, "%Y-%m-%d")
        result = expand(
            parse_rule(raw), start, start, datetime.datetime(2024, 3, 31, 23)
        )
        assert [value.date().isoformat() for value in result] == expected

    def test_reversed_window(self) -> None:
        anchor = datetime.datetime(2025, 1, 1)
        assert not expand(
            parse_rule("+1d"),
            anchor,
            anchor + datetime.timedelta(days=1),
            anchor,
        )

    def test_until_includes_whole_day(self) -> None:
        anchor = datetime.datetime(2025, 1, 1, 23, 59)
        result = expand(
            parse_rule("+1d @2025-01-02"),
            anchor,
            anchor,
            datetime.datetime(2025, 1, 3),
        )
        assert result == [anchor, datetime.datetime(2025, 1, 2, 23, 59)]


class TestBuilder:
    def test_python35_without_fold(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "version_info", (3, 5))
        assert Builder(2025, 1, 1).build() == datetime.datetime(2025, 1, 1)
        with pytest.raises(ValueError, match="fold requires"):
            Builder(2025, 1, 1, fold=1).build()


class TestEntryPoint:
    @pytest.mark.parametrize(
        "module,args,expected",
        [
            ("bonipy35", ["taskmd", "report", "MISSING"], 1),
            ("bonipy35.taskmd", ["report", "MISSING"], 1),
            (
                "bonipy35.taskmd",
                [
                    "schedule",
                    "conflicts",
                    "--from",
                    "2025-06-01",
                    "--to",
                    "2025-06-01",
                ],
                2,
            ),
        ],
    )
    def test_exit_codes(
        self,
        tmp_path: pathlib.Path,
        module: str,
        args: list[str],
        expected: int,
    ) -> None:
        path = tmp_path / "events.task.md"
        path.write_text(
            "# EVENT [2025-06-01T09:00Z--2025-06-01T11:00Z] A\n"
            "# EVENT [2025-06-01T10:00Z--2025-06-01T12:00Z] B\n"
        )
        if expected == 2:
            args = args + [str(path)]
        env = dict(os.environ, PYTHONPATH=str(pathlib.Path("src").resolve()))
        result = subprocess.run(
            [sys.executable, "-m", module] + args,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == expected, result.stderr


class TestLineRewriter:
    @pytest.mark.parametrize("text", ["last", "first\rlast"])
    def test_preserves_unterminated_last_line(self, text: str) -> None:
        assert LineRewriter(text).render() == text


class TestScheduleRunner:
    @pytest.mark.parametrize("command", ["show", "conflicts", "summary"])
    def test_default_arguments(
        self, tmp_path: pathlib.Path, command: str
    ) -> None:
        path = tmp_path / "empty.task.md"
        path.write_text("")
        runner = Runner(
            env=dict(
                os.environ, PYTHONPATH=str(pathlib.Path("src").resolve())
            )
        )
        function = {
            "show": schedule_show,
            "conflicts": schedule_conflicts,
            "summary": schedule_summary,
        }[command]
        assert function(runner, path).returncode == 0
