#!/usr/bin/env python3

# Standard libraries.
import datetime
import json
import pathlib

# Internal modules.
from bonipy35.taskmd import model
from bonipy35.taskmd import parser
from bonipy35.taskmd import schedule


def _utc(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0
) -> datetime.datetime:
    return datetime.datetime(
        year, month, day, hour, minute, tzinfo=datetime.timezone.utc
    )


def _parse(text: str) -> model.TaskFile:
    return parser.parse_string(text)


_TOP_LEVEL_EVENT = (
    "# EVENT [2025-09-01T10:00+00:00--2025-09-01T11:00+00:00] "
    "Sprint planning RECUR +1w :meeting:\n"
    "### CLOCK: [2025-09-01T10:08+00:00]--[2025-09-01T10:52+00:00]\n"
)

_TASK_NESTED_EVENT = (
    "# TODO Implement the parser :core:\n"
    "## EVENT [2025-09-01T10:30+00:00--2025-09-01T12:00+00:00] "
    "Overlapping meeting :meeting:\n"
)


class TestIterEvents:
    def test_top_level_event_has_own_tags(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        matches = list(schedule.iter_events(task_file))
        assert len(matches) == 1
        assert matches[0].tags == ["meeting"]
        assert matches[0].task is None

    def test_task_nested_event_inherits_task_tags(self) -> None:
        task_file = _parse(_TASK_NESTED_EVENT)
        matches = list(schedule.iter_events(task_file))
        assert len(matches) == 1
        assert matches[0].tags == ["core", "meeting"]
        assert matches[0].task is not None
        assert matches[0].task.title == "Implement the parser"

    def test_sub_events_are_included(self) -> None:
        task_file = _parse(
            "# EVENT [2025-09-01T10:00+00:00--2025-09-01T11:00+00:00] "
            "Sprint planning :meeting:\n"
            "## EVENT [2025-09-01T10:00+00:00--2025-09-01T10:15+00:00] "
            "Velocity review :agenda:\n"
        )
        matches = list(schedule.iter_events(task_file))
        assert len(matches) == 2
        assert matches[1].tags == ["meeting", "agenda"]


class TestMatchesEventFilter:
    def test_none_filter_matches_everything(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        match = list(schedule.iter_events(task_file))[0]
        assert schedule.matches_event_filter(match, None)

    def test_tag_filter(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        match = list(schedule.iter_events(task_file))[0]
        assert schedule.matches_event_filter(
            match, schedule.ScheduleFilter(tags=["meeting"])
        )
        assert not schedule.matches_event_filter(
            match, schedule.ScheduleFilter(tags=["nonexistent"])
        )

    def test_status_filter_requires_a_task(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        match = list(schedule.iter_events(task_file))[0]
        assert not schedule.matches_event_filter(
            match, schedule.ScheduleFilter(statuses=[model.Status.TODO])
        )

    def test_status_filter_checks_task_status(self) -> None:
        task_file = _parse(_TASK_NESTED_EVENT)
        match = list(schedule.iter_events(task_file))[0]
        assert schedule.matches_event_filter(
            match, schedule.ScheduleFilter(statuses=[model.Status.TODO])
        )
        assert not schedule.matches_event_filter(
            match, schedule.ScheduleFilter(statuses=[model.Status.DONE])
        )

    def test_no_inherited_tags_uses_own_tags_only(self) -> None:
        task_file = _parse(_TASK_NESTED_EVENT)
        match = list(schedule.iter_events(task_file))[0]
        filter_ = schedule.ScheduleFilter(
            tags=["core"], include_inherited_tags=False
        )
        assert not schedule.matches_event_filter(match, filter_)


class TestCollectOccurrences:
    def test_recurring_event_expands_within_window(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        occurrences = schedule.collect_occurrences(
            [task_file], _utc(2025, 9, 1), _utc(2025, 9, 15, 23)
        )
        assert len(occurrences) == 3
        assert occurrences[0].is_anchor
        assert not occurrences[1].is_anchor

    def test_filter_excludes_non_matching_events(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        occurrences = schedule.collect_occurrences(
            [task_file],
            _utc(2025, 9, 1),
            _utc(2025, 9, 15),
            schedule.ScheduleFilter(tags=["nonexistent"]),
        )
        assert not occurrences


class TestFormatDivergence:
    def test_no_clocks_returns_none(self) -> None:
        event = model.Event(
            level=1,
            scheduled_start=_utc(2025, 9, 1, 10),
            scheduled_end=_utc(2025, 9, 1, 11),
            title="e",
        )
        assert schedule.format_divergence(event) is None

    def test_late_and_short(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        event = task_file.events[0]
        divergence = schedule.format_divergence(event)
        assert divergence == "[+8m late, -8m short]"

    def test_exact_match_returns_none(self) -> None:
        event = model.Event(
            level=1,
            scheduled_start=_utc(2025, 9, 1, 10),
            scheduled_end=_utc(2025, 9, 1, 11),
            title="e",
            clocks=[
                model.ClockEntry(
                    start=_utc(2025, 9, 1, 10),
                    end=_utc(2025, 9, 1, 11),
                    description="",
                    work_notes="",
                )
            ],
        )
        assert schedule.format_divergence(event) is None


class TestRenderAgenda:
    def test_empty(self) -> None:
        assert schedule.render_agenda_text([]) == "(no events in range)"

    def test_text_groups_by_day_and_marks_recurring(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        occurrences = schedule.collect_occurrences(
            [task_file], _utc(2025, 9, 1), _utc(2025, 9, 8, 23)
        )
        text = schedule.render_agenda_text(occurrences)
        assert "Mon 2025-09-01" in text
        assert "Mon 2025-09-08" in text
        assert "(recurring)" in text
        assert "[+8m late, -8m short]" in text

    def test_json_round_trips(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        occurrences = schedule.collect_occurrences(
            [task_file], _utc(2025, 9, 1), _utc(2025, 9, 8)
        )
        payload = json.loads(schedule.render_agenda_json(occurrences))
        assert payload[0]["title"] == "Sprint planning"
        assert payload[0]["recurring"] is False


class TestFindConflicts:
    def test_overlapping_events_reported(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT + _TASK_NESTED_EVENT)
        occurrences = schedule.collect_occurrences(
            [task_file], _utc(2025, 9, 1), _utc(2025, 9, 1, 23)
        )
        conflicts = schedule.find_conflicts(occurrences)
        assert len(conflicts) == 1
        assert conflicts[0].overlap == datetime.timedelta(minutes=30)

    def test_render_text_and_json(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT + _TASK_NESTED_EVENT)
        occurrences = schedule.collect_occurrences(
            [task_file], _utc(2025, 9, 1), _utc(2025, 9, 1, 23)
        )
        conflicts = schedule.find_conflicts(occurrences)
        assert "overlaps" in schedule.render_conflicts_text(conflicts)
        payload = json.loads(schedule.render_conflicts_json(conflicts))
        assert len(payload) == 1

    def test_no_conflicts(self) -> None:
        assert schedule.render_conflicts_text([]) == "(no conflicts in range)"


class TestSummarize:
    def test_group_by_tag(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        groups = schedule.summarize(
            [task_file],
            _utc(2025, 9, 1),
            _utc(2025, 9, 15, 23),
            group_by="tag",
        )
        assert groups["meeting"].count == 3
        assert groups["meeting"].actual == datetime.timedelta(minutes=44)

    def test_group_by_task(self) -> None:
        task_file = _parse(_TASK_NESTED_EVENT)
        groups = schedule.summarize(
            [task_file],
            _utc(2025, 9, 1),
            _utc(2025, 9, 2),
            group_by="task",
        )
        assert "Implement the parser" in groups

    def test_group_by_day_and_week(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        by_day = schedule.summarize(
            [task_file],
            _utc(2025, 9, 1),
            _utc(2025, 9, 15),
            group_by="day",
        )
        assert "2025-09-01" in by_day
        by_week = schedule.summarize(
            [task_file],
            _utc(2025, 9, 1),
            _utc(2025, 9, 15),
            group_by="week",
        )
        assert any("-W" in key for key in by_week)

    def test_untagged_events_grouped_together(self) -> None:
        task_file = _parse(
            "# EVENT [2025-09-01T10:00+00:00--2025-09-01T11:00+00:00] "
            "No tags\n"
        )
        groups = schedule.summarize(
            [task_file], _utc(2025, 9, 1), _utc(2025, 9, 2)
        )
        assert "(untagged)" in groups

    def test_render_text_and_json(self) -> None:
        task_file = _parse(_TOP_LEVEL_EVENT)
        groups = schedule.summarize(
            [task_file], _utc(2025, 9, 1), _utc(2025, 9, 15)
        )
        text = schedule.render_summary_text(groups)
        assert "Total:" in text
        payload = json.loads(schedule.render_summary_json(groups))
        assert "meeting" in payload

    def test_render_empty(self) -> None:
        assert schedule.render_summary_text({}) == "(no events in range)"


class TestCli:
    def test_show_end_to_end(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "notes.task.md"
        path.write_text(_TOP_LEVEL_EVENT, encoding="utf-8")
        exit_code = schedule.main(
            [
                "cli",
                "show",
                str(path),
                "--from",
                "2025-09-01",
                "--to",
                "2025-09-15",
            ]
        )
        assert exit_code == 0

    def test_conflicts_end_to_end_exit_code(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = tmp_path / "notes.task.md"
        path.write_text(
            _TOP_LEVEL_EVENT + _TASK_NESTED_EVENT, encoding="utf-8"
        )
        exit_code = schedule.main(
            [
                "cli",
                "conflicts",
                str(path),
                "--from",
                "2025-09-01",
                "--to",
                "2025-09-02",
            ]
        )
        assert exit_code == 2

    def test_summary_end_to_end(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "notes.task.md"
        path.write_text(_TOP_LEVEL_EVENT, encoding="utf-8")
        exit_code = schedule.main(
            [
                "cli",
                "summary",
                str(path),
                "--from",
                "2025-09-01",
                "--to",
                "2025-09-15",
                "--format",
                "json",
            ]
        )
        assert exit_code == 0

    def test_no_subcommand(self) -> None:
        assert schedule.main(["cli"]) == 1

    def test_missing_input(self) -> None:
        assert schedule.main(["cli", "show"]) == 1

    def test_missing_file(self, tmp_path: pathlib.Path) -> None:
        missing = tmp_path / "missing.task.md"
        assert schedule.main(["cli", "show", str(missing)]) == 1
