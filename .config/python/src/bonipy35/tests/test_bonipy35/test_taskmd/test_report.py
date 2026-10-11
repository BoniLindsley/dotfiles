#!/usr/bin/env python3

# Standard libraries.
import csv
import datetime
import io
import json
import pathlib
import typing

from typing import List, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.taskmd.__main__ import main
from bonipy35.taskmd import model
from bonipy35.taskmd import parser
from bonipy35.taskmd import report

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def fixture_path(name: str) -> pathlib.Path:
    return _FIXTURES_DIR / name


def _utc(*args: typing.Any, **kwargs: typing.Any) -> datetime.datetime:
    kwargs.setdefault("tzinfo", datetime.timezone.utc)
    return datetime.datetime(*args, **kwargs)


def _clock(
    start: datetime.datetime,
    end: Union[None, datetime.datetime] = None,
    description: str = "",
) -> model.ClockEntry:
    return model.ClockEntry(
        start=start, end=end, description=description, work_notes=""
    )


def _task(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    title: str,
    status: model.Status = model.Status.TODO,
    tags: Union[None, List[str]] = None,
    level: int = 1,
    clocks: Union[None, List[model.ClockEntry]] = None,
    tasks: Union[None, List[model.Task]] = None,
) -> model.Task:
    return model.Task(
        level=level,
        status=status,
        title=title,
        tags=tags or [],
        clocks=clocks or [],
        tasks=tasks or [],
    )


class TestFilterConstructorDefaults:
    def test_include_inherited_tags_none_defaults_to_true(self) -> None:
        f = report.Filter(include_inherited_tags=None)
        assert f.include_inherited_tags is True


class TestReportNodeConstructorDefaults:
    def test_children_defaults_to_empty_list(self) -> None:
        task = model.Task(level=1, status=model.Status.TODO, title="t")
        node = report.ReportNode(
            own_duration=datetime.timedelta(0),
            task=task,
            total_duration=datetime.timedelta(0),
        )
        assert node.children == []


class TestFormatDuration:
    def test_zero(self) -> None:
        assert report.format_duration(datetime.timedelta(0)) == "0m"

    def test_minutes_only(self) -> None:
        assert report.format_duration(datetime.timedelta(minutes=45)) == "45m"

    def test_hours_and_minutes(self) -> None:
        assert (
            report.format_duration(
                datetime.timedelta(hours=2, minutes=30),
            )
            == "2h 30m"
        )

    def test_hours_pad_zero_minutes(self) -> None:
        assert report.format_duration(datetime.timedelta(hours=1)) == "1h 00m"

    def test_negative_duration(self) -> None:
        assert (
            report.format_duration(datetime.timedelta(minutes=-16)) == "-16m"
        )

    def test_negative_hours(self) -> None:
        assert (
            report.format_duration(
                datetime.timedelta(hours=-1, minutes=-30),
            )
            == "-1h 30m"
        )


class TestFilterTasksStatus:
    def test_no_status_filter_keeps_everything(self) -> None:
        tasks = [
            _task("a", status=model.Status.TODO),
            _task("b", status=model.Status.DONE),
        ]
        kept = report.filter_tasks(tasks, report.Filter())
        assert [t.title for t in kept] == ["a", "b"]

    def test_status_filter_keeps_only_matching(self) -> None:
        tasks = [
            _task("a", status=model.Status.TODO),
            _task("b", status=model.Status.DONE),
        ]
        kept = report.filter_tasks(
            tasks, report.Filter(statuses=[model.Status.DONE])
        )
        assert [t.title for t in kept] == ["b"]

    def test_status_filter_multiple_values_is_or(self) -> None:
        tasks = [
            _task("a", status=model.Status.TODO),
            _task("b", status=model.Status.DONE),
            _task("c", status=model.Status.DROP),
        ]
        kept = report.filter_tasks(
            tasks,
            report.Filter(statuses=[model.Status.TODO, model.Status.DROP]),
        )
        assert [t.title for t in kept] == ["a", "c"]


class TestFilterTasksTags:
    def test_no_tag_filter_keeps_everything(self) -> None:
        tasks = [_task("a", tags=["x"]), _task("b", tags=[])]
        kept = report.filter_tasks(tasks, report.Filter())
        assert len(kept) == 2

    def test_tag_filter_keeps_matching_own_tag(self) -> None:
        tasks = [_task("a", tags=["python"]), _task("b", tags=["docs"])]
        kept = report.filter_tasks(tasks, report.Filter(tags=["python"]))
        assert [t.title for t in kept] == ["a"]

    def test_tag_filter_multiple_tags_requires_all(self) -> None:
        tasks = [
            _task("a", tags=["python", "core"]),
            _task("b", tags=["python"]),
        ]
        kept = report.filter_tasks(
            tasks,
            report.Filter(tags=["python", "core"]),
        )
        assert [t.title for t in kept] == ["a"]

    def test_tag_filter_matches_inherited_tag(self) -> None:
        child = _task("child", level=2, tags=[])
        parent = _task("parent", level=1, tags=["release"], tasks=[child])
        kept = report.filter_tasks([parent], report.Filter(tags=["release"]))
        assert len(kept) == 1
        # Child is kept too, since it's a descendant of a match and
        # inherits the matching tag.
        assert kept[0].tasks[0].title == "child"

    def test_no_inherited_tags_excludes_non_matching_child(self) -> None:
        child = _task("child", level=2, tags=[])
        parent = _task("parent", level=1, tags=["release"], tasks=[child])
        kept = report.filter_tasks(
            [parent],
            report.Filter(tags=["release"], include_inherited_tags=False),
        )
        # Parent matches on its own tag and is kept. Matching only
        # cascades *upward* (a matching descendant keeps its
        # ancestors as context); it does not cascade back down, so
        # the child -- which has no own tag and, with inheritance
        # off, doesn't inherit "release" either -- is pruned.
        assert len(kept) == 1
        assert kept[0].title == "parent"
        assert kept[0].tasks == []

    def test_no_inherited_tags_child_only_match_is_pruned(self) -> None:
        # Child has the tag itself; parent does not. With inheritance
        # off this doesn't matter for the child (it has its own tag),
        # but a *grandchild* with no own tag should not match via the
        # child's tag when inheritance is off.
        grandchild = _task("grandchild", level=3, tags=[])
        child = _task("child", level=2, tags=["x"], tasks=[grandchild])
        parent = _task("parent", level=1, tags=[], tasks=[child])
        kept = report.filter_tasks(
            [parent],
            report.Filter(tags=["x"], include_inherited_tags=False),
        )
        assert len(kept) == 1
        assert len(kept[0].tasks) == 1
        assert kept[0].tasks[0].tasks == []

    def test_child_match_keeps_non_matching_parent_as_context(self) -> None:
        child = _task("child", level=2, tags=["python"])
        parent = _task("parent", level=1, tags=["docs"], tasks=[child])
        kept = report.filter_tasks([parent], report.Filter(tags=["python"]))
        assert len(kept) == 1
        assert kept[0].title == "parent"
        assert [c.title for c in kept[0].tasks] == ["child"]

    def test_no_match_anywhere_prunes_entire_subtree(self) -> None:
        child = _task("child", level=2, tags=["docs"])
        parent = _task("parent", level=1, tags=["docs"], tasks=[child])
        kept = report.filter_tasks([parent], report.Filter(tags=["python"]))
        assert not kept


class TestFilterTasksDateRange:
    def test_from_date_excludes_sessions_ending_before(self) -> None:
        early = _clock(_utc(2025, 6, 1), _utc(2025, 6, 1, 1))
        late = _clock(_utc(2025, 6, 10), _utc(2025, 6, 10, 1))
        task = _task("t", clocks=[early, late])
        kept = report.filter_tasks(
            [task],
            report.Filter(from_date=datetime.date(2025, 6, 5)),
        )
        assert len(kept[0].clocks) == 1
        assert kept[0].clocks[0] is late

    def test_to_date_excludes_sessions_starting_after(self) -> None:
        early = _clock(_utc(2025, 6, 1), _utc(2025, 6, 1, 1))
        late = _clock(_utc(2025, 6, 10), _utc(2025, 6, 10, 1))
        task = _task("t", clocks=[early, late])
        kept = report.filter_tasks(
            [task],
            report.Filter(to_date=datetime.date(2025, 6, 5)),
        )
        assert len(kept[0].clocks) == 1
        assert kept[0].clocks[0] is early

    def test_open_session_always_passes_from_date(self) -> None:
        open_clock = _clock(_utc(2025, 1, 1))
        task = _task("t", clocks=[open_clock])
        kept = report.filter_tasks(
            [task],
            report.Filter(from_date=datetime.date(2025, 12, 31)),
        )
        assert len(kept[0].clocks) == 1

    def test_open_session_still_subject_to_to_date(self) -> None:
        open_clock = _clock(_utc(2025, 12, 31))
        task = _task("t", clocks=[open_clock])
        kept = report.filter_tasks(
            [task],
            report.Filter(to_date=datetime.date(2025, 1, 1)),
        )
        assert kept[0].clocks == []

    def test_task_with_no_matching_sessions_but_matching_tag_is_kept_with_zero_clocks(
        self,
    ) -> None:
        clock = _clock(_utc(2025, 1, 1), _utc(2025, 1, 1, 1))
        task = _task("t", tags=["x"], clocks=[clock])
        kept = report.filter_tasks(
            [task],
            report.Filter(tags=["x"], from_date=datetime.date(2025, 12, 31)),
        )
        assert len(kept) == 1
        assert kept[0].clocks == []


class TestAggregate:
    def test_task_events_contribute_to_own_duration(self) -> None:
        event = model.Event(
            level=2,
            scheduled_start=_utc(2025, 1, 1, 10),
            scheduled_end=_utc(2025, 1, 1, 11),
            title="Sprint planning",
            clocks=[
                _clock(_utc(2025, 1, 1, 10, 5), _utc(2025, 1, 1, 10, 50))
            ],
        )
        task = _task("t", clocks=[])
        task.events.append(event)
        tf = model.TaskFile(path=None, tasks=[task])
        nodes = report.aggregate(tf)
        assert nodes[0].own_duration == datetime.timedelta(minutes=45)

    def test_own_and_total_duration(self) -> None:
        child = _task(
            "child",
            level=2,
            clocks=[_clock(_utc(2025, 1, 1, 9), _utc(2025, 1, 1, 10))],
        )
        parent = _task(
            "parent",
            level=1,
            tasks=[child],
            clocks=[_clock(_utc(2025, 1, 1, 8), _utc(2025, 1, 1, 8, 30))],
        )
        tf = model.TaskFile(path=None, tasks=[parent])
        nodes = report.aggregate(tf)
        assert len(nodes) == 1
        assert nodes[0].own_duration == datetime.timedelta(minutes=30)
        assert nodes[0].total_duration == datetime.timedelta(
            hours=1, minutes=30
        )
        assert nodes[0].children[0].own_duration == datetime.timedelta(
            hours=1
        )
        assert nodes[0].children[0].total_duration == datetime.timedelta(
            hours=1
        )

    def test_grand_total_sums_top_level_only_no_double_counting(self) -> None:
        child = _task(
            "child",
            level=2,
            clocks=[_clock(_utc(2025, 1, 1, 9), _utc(2025, 1, 1, 10))],
        )
        parent = _task("parent", level=1, tasks=[child])
        sibling = _task(
            "sibling",
            level=1,
            clocks=[_clock(_utc(2025, 1, 1, 9), _utc(2025, 1, 1, 9, 15))],
        )
        tf = model.TaskFile(path=None, tasks=[parent, sibling])
        nodes = report.aggregate(tf)
        assert report.grand_total(nodes) == datetime.timedelta(
            hours=1, minutes=15
        )

    def test_aggregate_applies_filter(self) -> None:
        matching = _task("a", tags=["x"])
        other = _task("b", tags=["y"])
        tf = model.TaskFile(path=None, tasks=[matching, other])
        nodes = report.aggregate(tf, report.Filter(tags=["x"]))
        assert [n.task.title for n in nodes] == ["a"]

    def test_aggregate_default_filter_keeps_everything(self) -> None:
        tf = model.TaskFile(path=None, tasks=[_task("a"), _task("b")])
        nodes = report.aggregate(tf)
        assert len(nodes) == 2


class TestRenderText:
    def test_includes_file_label_and_grand_total(self) -> None:
        tf = model.TaskFile(
            path=None, tasks=[_task("Write the parser", tags=["core"])]
        )
        nodes = report.aggregate(tf)
        text = report.render_text(nodes, file_label="example.task.md")
        lines = text.splitlines()
        assert lines[0] == "example.task.md"
        assert "Write the parser" in lines[1]
        assert lines[-1].startswith("Grand total")

    def test_indentation_reflects_nesting(self) -> None:
        child = _task("child", level=2)
        parent = _task("parent", level=1, tasks=[child])
        tf = model.TaskFile(path=None, tasks=[parent])
        nodes = report.aggregate(tf)
        text = report.render_text(nodes, file_label="f.task.md")
        lines = text.splitlines()
        parent_line = next(l for l in lines if "parent" in l)
        child_line = next(l for l in lines if "child" in l)
        parent_indent = len(parent_line) - len(parent_line.lstrip(" "))
        child_indent = len(child_line) - len(child_line.lstrip(" "))
        assert child_indent > parent_indent

    def test_show_sessions_includes_time_range(self) -> None:
        clock = _clock(_utc(2025, 6, 9, 9), _utc(2025, 6, 9, 10), "work")
        task = _task("t", clocks=[clock])
        tf = model.TaskFile(path=None, tasks=[task])
        nodes = report.aggregate(tf)
        text = report.render_text(
            nodes, file_label="f.task.md", show_sessions=True
        )
        assert "work" in text
        assert "2025-06-09T09:00" in text

    def test_open_session_shown_as_open(self) -> None:
        clock = _clock(_utc(2025, 6, 9, 9))
        task = _task("t", clocks=[clock])
        tf = model.TaskFile(path=None, tasks=[task])
        nodes = report.aggregate(tf)
        text = report.render_text(
            nodes, file_label="f.task.md", show_sessions=True
        )
        assert "(open)" in text

    def test_no_file_label_omits_header_line(self) -> None:
        tf = model.TaskFile(path=None, tasks=[_task("t")])
        nodes = report.aggregate(tf)
        text = report.render_text(nodes)
        assert not text.startswith("None")
        assert "[TODO] t" in text.splitlines()[0]

    def test_very_long_title_still_renders_with_minimal_padding(self) -> None:
        # When the label alone exceeds the fixed rule width, padding
        # clamps to a single space instead of going negative.
        long_title = "x" * 80
        tf = model.TaskFile(path=None, tasks=[_task(long_title)])
        nodes = report.aggregate(tf)
        text = report.render_text(nodes, file_label="f.task.md")
        task_line = next(l for l in text.splitlines() if long_title in l)
        assert task_line.endswith("0m")

    def test_very_long_grand_total_label_clamps_padding(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(report, "RULE_WIDTH", 10)
        tf = model.TaskFile(path=None, tasks=[_task("t")])
        nodes = report.aggregate(tf)
        text = report.render_text(nodes, file_label="f.task.md")
        assert "Grand total" in text


class TestRenderMultiText:
    def test_single_file_no_combined_total_line(self) -> None:
        tf = model.TaskFile(path=None, tasks=[_task("t")])
        nodes = report.aggregate(tf)
        text = report.render_multi_text([("f.task.md", nodes)])
        assert "all files" not in text

    def test_multiple_files_adds_combined_total(self) -> None:
        tf1 = model.TaskFile(
            path=None,
            tasks=[
                _task(
                    "a",
                    clocks=[
                        _clock(_utc(2025, 1, 1, 9), _utc(2025, 1, 1, 10))
                    ],
                ),
            ],
        )
        tf2 = model.TaskFile(
            path=None,
            tasks=[
                _task(
                    "b",
                    clocks=[
                        _clock(_utc(2025, 1, 1, 9), _utc(2025, 1, 1, 9, 30))
                    ],
                ),
            ],
        )
        sections = [
            ("one.task.md", report.aggregate(tf1)),
            ("two.task.md", report.aggregate(tf2)),
        ]
        text = report.render_multi_text(sections)
        assert "Grand total (all files)" in text
        assert "1h 30m" in text

    def test_combined_total_padding_clamps_for_narrow_width(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(report, "RULE_WIDTH", 5)
        tf1 = model.TaskFile(path=None, tasks=[_task("a")])
        tf2 = model.TaskFile(path=None, tasks=[_task("b")])
        sections = [
            ("one.task.md", report.aggregate(tf1)),
            ("two.task.md", report.aggregate(tf2)),
        ]
        text = report.render_multi_text(sections)
        assert "Grand total (all files)" in text


class TestRenderJson:
    def test_structure_round_trips(self) -> None:
        clock = _clock(_utc(2025, 1, 1, 9), _utc(2025, 1, 1, 10, 30))
        task = _task("t", tags=["a"], clocks=[clock])
        tf = model.TaskFile(path=None, tasks=[task])
        nodes = report.aggregate(tf)
        payload = json.loads(report.render_json([("f.task.md", nodes)]))
        assert payload["files"][0]["file"] == "f.task.md"
        task_json = payload["files"][0]["tasks"][0]
        assert task_json["title"] == "t"
        assert task_json["tags"] == ["a"]
        assert task_json["own_duration"] == "1h 30m"
        assert payload["grand_total"] == "1h 30m"

    def test_show_sessions_includes_session_list(self) -> None:
        clock = _clock(_utc(2025, 1, 1, 9), None, "ongoing")
        task = _task("t", clocks=[clock])
        tf = model.TaskFile(path=None, tasks=[task])
        nodes = report.aggregate(tf)
        payload = json.loads(
            report.render_json([("f.task.md", nodes)], show_sessions=True),
        )
        session = payload["files"][0]["tasks"][0]["sessions"][0]
        assert session["end"] is None
        assert session["description"] == "ongoing"

    def test_without_show_sessions_no_session_key(self) -> None:
        task = _task("t")
        tf = model.TaskFile(path=None, tasks=[task])
        nodes = report.aggregate(tf)
        payload = json.loads(report.render_json([("f.task.md", nodes)]))
        assert "sessions" not in payload["files"][0]["tasks"][0]

    def test_children_nested_recursively(self) -> None:
        child = _task("child", level=2)
        parent = _task("parent", level=1, tasks=[child])
        tf = model.TaskFile(path=None, tasks=[parent])
        nodes = report.aggregate(tf)
        payload = json.loads(report.render_json([("f.task.md", nodes)]))
        assert (
            payload["files"][0]["tasks"][0]["children"][0]["title"] == "child"
        )


class TestRenderCsv:
    def test_one_row_per_task_depth_first(self) -> None:
        child = _task("child", level=2, tags=["x"])
        parent = _task("parent", level=1, tags=["y"], tasks=[child])
        tf = model.TaskFile(path=None, tasks=[parent])
        nodes = report.aggregate(tf)
        text = report.render_csv([("f.task.md", nodes)])
        rows = list(csv.DictReader(io.StringIO(text)))
        assert [r["title"] for r in rows] == ["parent", "child"]
        assert rows[0]["tags"] == "y"
        assert rows[1]["level"] == "2"

    def test_header_row_present(self) -> None:
        tf = model.TaskFile(path=None, tasks=[_task("t")])
        text = report.render_csv([("f.task.md", report.aggregate(tf))])
        header = text.splitlines()[0]
        assert header == ",".join(report.CSV_FIELDNAMES)

    def test_multiple_files_all_rows_present(self) -> None:
        tf1 = model.TaskFile(path=None, tasks=[_task("a")])
        tf2 = model.TaskFile(path=None, tasks=[_task("b")])
        sections = [
            ("one.task.md", report.aggregate(tf1)),
            ("two.task.md", report.aggregate(tf2)),
        ]
        rows = list(csv.DictReader(io.StringIO(report.render_csv(sections))))
        assert [r["file"] for r in rows] == ["one.task.md", "two.task.md"]


class TestDiscoverPaths:
    def test_explicit_files_returned_in_order(self) -> None:
        paths = report.discover_paths(
            files=[
                str(fixture_path("basic.task.md")),
                str(fixture_path("clocked.task.md")),
            ],
        )
        assert [p.name for p in paths] == ["basic.task.md", "clocked.task.md"]

    def test_directory_scan_finds_task_md_files(self) -> None:
        paths = report.discover_paths(directory=str(_FIXTURES_DIR))
        names = {p.name for p in paths}
        assert {
            "basic.task.md",
            "clocked.task.md",
            "nested.task.md",
        }.issubset(names)

    def test_magic_comment_md_file_is_discovered(
        self, tmp_path: pathlib.Path
    ) -> None:
        marked = tmp_path / "notes.md"
        marked.write_text("<!-- taskmd -->\n# TODO from magic comment\n")
        plain = tmp_path / "readme.md"
        plain.write_text("# Just a heading, not taskmd\n")
        paths = report.discover_paths(directory=str(tmp_path))
        names = {p.name for p in paths}
        assert "notes.md" in names
        assert "readme.md" not in names

    def test_depth_limit_excludes_deeper_files(
        self, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "top.task.md").write_text("# TODO top\n")
        nested_dir = tmp_path / "nested"
        nested_dir.mkdir()
        (nested_dir / "deep.task.md").write_text("# TODO deep\n")
        shallow_paths = report.discover_paths(
            directory=str(tmp_path), depth=0
        )
        assert {p.name for p in shallow_paths} == {"top.task.md"}
        deep_paths = report.discover_paths(directory=str(tmp_path), depth=1)
        assert {p.name for p in deep_paths} == {"top.task.md", "deep.task.md"}

    def test_duplicate_paths_are_deduplicated(self) -> None:
        path_str = str(fixture_path("basic.task.md"))
        paths = report.discover_paths(files=[path_str, path_str])
        assert len(paths) == 1

    def test_no_files_or_dir_returns_empty(self) -> None:
        assert not report.discover_paths()

    def test_non_md_file_in_scanned_dir_is_ignored(
        self, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "notes.txt").write_text("not markdown at all\n")
        (tmp_path / "real.task.md").write_text("# TODO real\n")
        paths = report.discover_paths(directory=str(tmp_path))
        assert {p.name for p in paths} == {"real.task.md"}

    def test_non_utf8_md_file_is_skipped_not_raised(
        self, tmp_path: pathlib.Path
    ) -> None:
        binary_md = tmp_path / "binary.md"
        binary_md.write_bytes(b"\xff\xfe\x00\x01 not valid utf-8")
        paths = report.discover_paths(directory=str(tmp_path))
        assert not paths


class TestFixtureIntegration:
    def test_clocked_fixture_totals(self) -> None:
        tf = parser.parse_file(fixture_path("clocked.task.md"))
        nodes = report.aggregate(tf)
        by_title = {n.task.title: n for n in nodes}
        assert by_title[
            "Write the parser"
        ].total_duration == datetime.timedelta(
            hours=5,
            minutes=15,
        )
        assert by_title["Add logging"].total_duration == datetime.timedelta(
            hours=1,
            minutes=30,
        )
        assert report.grand_total(nodes) == datetime.timedelta(
            hours=6, minutes=45
        )

    def test_nested_fixture_totals_roll_up(self) -> None:
        tf = parser.parse_file(fixture_path("nested.task.md"))
        nodes = report.aggregate(tf)
        top = next(n for n in nodes if n.task.title == "Ship taskmd v0.1")
        write_parser_node = next(
            c for c in top.children if c.task.title == "Write the parser"
        )
        assert write_parser_node.total_duration == datetime.timedelta(
            hours=1,
            minutes=45,
        )
        assert top.total_duration == datetime.timedelta(hours=1, minutes=45)

    def test_clocked_fixture_from_date_filter(self) -> None:
        tf = parser.parse_file(fixture_path("clocked.task.md"))
        nodes = report.aggregate(
            tf,
            report.Filter(from_date=datetime.date(2025, 6, 10)),
        )
        by_title = {n.task.title: n for n in nodes}
        # The first (2025-06-09) closed session is excluded; the
        # second (2025-06-10) closed session and the open one remain.
        assert by_title[
            "Write the parser"
        ].total_duration == datetime.timedelta(
            hours=3,
            minutes=30,
        )

    def test_basic_fixture_tag_filter(self) -> None:
        tf = parser.parse_file(fixture_path("basic.task.md"))
        nodes = report.aggregate(tf, report.Filter(tags=["core"]))
        titles = {n.task.title for n in nodes}
        assert titles == {"Write the parser", "Add logging"}


class TestCliReport:
    def test_text_output_exit_zero(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(
            ["taskmd", "report", str(fixture_path("clocked.task.md"))]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Grand total" in captured.out
        assert "5h 15m" in captured.out

    def test_nonexistent_file_reports_cleanly(
        self, capsys: pytest.CaptureFixture[str], tmp_path: pathlib.Path
    ) -> None:
        missing = tmp_path / "missing.task.md"
        exit_code = main(["taskmd", "report", str(missing)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "No such file" in captured.err

    def test_json_output_is_valid_json(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(
            [
                "taskmd",
                "report",
                str(fixture_path("clocked.task.md")),
                "--format",
                "json",
            ],
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["files"][0]["file"] == str(
            fixture_path("clocked.task.md")
        )

    def test_csv_output_has_header(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(
            [
                "taskmd",
                "report",
                str(fixture_path("basic.task.md")),
                "--format",
                "csv",
            ],
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.splitlines()[0] == ",".join(report.CSV_FIELDNAMES)

    def test_tag_filter_via_cli(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(
            [
                "taskmd",
                "report",
                str(fixture_path("basic.task.md")),
                "--tag",
                "core",
            ],
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Write the parser" in captured.out
        assert "Get design sign-off" not in captured.out

    def test_status_filter_via_cli(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(
            [
                "taskmd",
                "report",
                str(fixture_path("basic.task.md")),
                "--status",
                "DONE",
            ],
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Add logging" in captured.out
        assert "Write the parser" not in captured.out

    def test_no_input_files_is_an_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["taskmd", "report"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "no input files" in captured.err

    def test_dir_flag_via_cli(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["taskmd", "report", "--dir", str(_FIXTURES_DIR)])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "basic.task.md" in captured.out
        assert "clocked.task.md" in captured.out
        assert "nested.task.md" in captured.out

    def test_lenient_flag_accepts_lowercase_status(
        self, capsys: pytest.CaptureFixture[str], tmp_path: pathlib.Path
    ) -> None:
        lenient_file = tmp_path / "lower.task.md"
        lenient_file.write_text("# todo lowercase status\nSome notes.\n")
        exit_code = main(["taskmd", "report", str(lenient_file), "--lenient"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "[TODO] lowercase status" in captured.out

    def test_strict_mode_parse_error_reported_and_nonzero_exit(
        self, capsys: pytest.CaptureFixture[str], tmp_path: pathlib.Path
    ) -> None:
        bad_file = tmp_path / "bad.task.md"
        bad_file.write_text("# todo lowercase status\n")
        exit_code = main(["taskmd", "report", str(bad_file)])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert str(bad_file) in captured.err

    def test_invalid_date_argument_reports_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "taskmd",
                    "report",
                    str(fixture_path("basic.task.md")),
                    "--from",
                    "not-a-date",
                ],
            )
        assert exc_info.value.code != 0
        captured = capsys.readouterr()
        assert "not a valid ISO-8601 date" in captured.err
