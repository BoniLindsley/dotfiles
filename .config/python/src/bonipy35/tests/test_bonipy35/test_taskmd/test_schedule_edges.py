#!/usr/bin/env python3

# Standard libraries.
import json
import pathlib

# External dependencies.
import pytest

# Internal modules.
from bonipy35.taskmd.parser import parse_string
from bonipy35.taskmd.schedule import (
    ScheduleFilter,
    collect_occurrences,
    find_conflicts,
    iter_events,
    main,
    render_agenda_text,
    summarize,
)

_EVENT = "# EVENT [2025-06-01T09:00Z--2025-06-01T10:00Z] A\n"


class TestScheduleFilter:
    def test_none_defaults(self) -> None:
        filter_ = ScheduleFilter(include_inherited_tags=None)
        assert filter_.include_inherited_tags
        assert not filter_.tags
        assert not filter_.statuses


class TestIterEvents:
    def test_duplicate_inherited_tag_is_deduplicated(self) -> None:
        parsed = parse_string(
            "# TODO task :x:\n" + "#" + _EVENT.rstrip() + " :x:\n"
        )
        assert list(iter_events(parsed))[0].tags == ["x"]


class TestRenderAgendaText:
    def test_same_day_untagged_events_and_divergence(self) -> None:
        parsed = parse_string(
            _EVENT
            + "## CLOCK: [2025-06-01T09:15Z]--[2025-06-01T09:45Z]\n"
            + "# EVENT [2025-06-01T11:00Z--2025-06-01T12:00Z] B\n"
        )
        start = parsed.events[0].scheduled_start
        end = parsed.events[-1].scheduled_end
        text = render_agenda_text(collect_occurrences([parsed], start, end))
        assert text.count("Sun 2025-06-01") == 1
        assert "[+15m late, -15m short]" in text
        assert "B" in text


class TestFindConflicts:
    def test_touching_and_zero_duration_events_do_not_conflict(self) -> None:
        parsed = parse_string(
            _EVENT
            + "# EVENT [2025-06-01T09:30Z--2025-06-01T09:30Z] Empty\n"
            + "# EVENT [2025-06-01T10:00Z--2025-06-01T11:00Z] B\n"
        )
        assert not find_conflicts(
            collect_occurrences(
                [parsed],
                parsed.events[0].scheduled_start,
                parsed.events[-1].scheduled_end,
            )
        )


class TestSummarize:
    def test_tag_filter_excludes_events(self) -> None:
        parsed = parse_string(_EVENT)
        event = parsed.events[0]
        assert not summarize(
            [parsed],
            event.scheduled_start,
            event.scheduled_end,
            filter_=ScheduleFilter(tags=["missing"]),
        )

    def test_invalid_group_is_rejected(self) -> None:
        parsed = parse_string(_EVENT)
        event = parsed.events[0]
        with pytest.raises(ValueError, match="unknown group_by"):
            summarize(
                [parsed],
                event.scheduled_start,
                event.scheduled_end,
                group_by="unknown",
            )


class TestMain:
    @pytest.mark.parametrize("command", ["show", "conflicts", "summary"])
    def test_missing_files_fail(
        self,
        tmp_path: pathlib.Path,
        command: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert main(["schedule", command, str(tmp_path / "missing")]) == 1
        assert "No such file" in capsys.readouterr().err

    @pytest.mark.parametrize("command", ["show", "conflicts", "summary"])
    def test_parse_errors_fail(
        self,
        tmp_path: pathlib.Path,
        command: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = tmp_path / "bad.task.md"
        path.write_text("# EVENT [not-a-date] E\n")
        assert main(["schedule", command, str(path)]) == 1
        assert "malformed EVENT span" in capsys.readouterr().err

    @pytest.mark.parametrize("command", ["show", "conflicts", "summary"])
    @pytest.mark.parametrize("format_", ["json", "text"])
    def test_output_formats(
        self,
        tmp_path: pathlib.Path,
        command: str,
        format_: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = tmp_path / "events.task.md"
        path.write_text(_EVENT)
        assert (
            main(
                [
                    "schedule",
                    command,
                    str(path),
                    "--from",
                    "2025-06-01",
                    "--to",
                    "2025-06-01",
                    "--format",
                    format_,
                ]
            )
            == 0
        )
        output = capsys.readouterr().out
        if format_ == "json":
            json.loads(output)
        else:
            assert output.strip()

    def test_invalid_date_is_argument_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as caught:
            main(["schedule", "show", "--from", "2025-02-30"])
        assert caught.value.code == 2
        assert "not a valid ISO-8601 date" in capsys.readouterr().err
