#!/usr/bin/env python3

# Standard libraries.
import datetime
import json
import pathlib
import shutil

# External dependencies.
import pytest

# Internal modules.
from bonipy35.taskmd import clock
from bonipy35.taskmd import model
from bonipy35.taskmd import parser

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def _copy_fixture(name: str, tmp_path: pathlib.Path) -> pathlib.Path:
    destination = tmp_path / name
    shutil.copy(_FIXTURES_DIR / name, destination)
    return destination


def _utc(
    year: int, month: int, day: int, hour: int, minute: int
) -> datetime.datetime:
    return datetime.datetime(
        year, month, day, hour, minute, tzinfo=datetime.timezone.utc
    )


# ---------------------------------------------------------------------------
# compute_bounds / find_task_at_line
# ---------------------------------------------------------------------------


class TestFindTaskAtLine:
    def test_finds_top_level_task(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        task = clock.find_task_at_line(task_file, 2)
        assert task is not None
        assert task.title == "Write the parser"

    def test_finds_innermost_nested_task(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("nested.task.md", tmp_path)
        task_file = parser.parse_file(path)
        # Line 9 is inside "Handle edge cases" (a level-3 subtask),
        # which is itself inside "Write the parser" and "Ship v0.1".
        task = clock.find_task_at_line(task_file, 9)
        assert task is not None
        assert task.title == "Handle edge cases"

    def test_finds_parent_when_line_is_in_parents_own_content(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        path = _copy_fixture("nested.task.md", tmp_path)
        task_file = parser.parse_file(path)
        # Line 5 is "Write the parser"'s own description, before any
        # subtask heading.
        task = clock.find_task_at_line(task_file, 5)
        assert task is not None
        assert task.title == "Write the parser"

    def test_line_at_exact_heading_matches_that_task(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        task = clock.find_task_at_line(task_file, 1)
        assert task is not None
        assert task.title == "Write the parser"

    def test_line_past_end_of_file_returns_none(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        assert clock.find_task_at_line(task_file, 9999) is None

    def test_line_zero_returns_none(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        assert clock.find_task_at_line(task_file, 0) is None

    def test_empty_task_file_returns_none(self) -> None:
        task_file = model.TaskFile(path=None, total_lines=10)
        assert clock.find_task_at_line(task_file, 5) is None

    def test_last_tasks_range_is_capped_at_total_lines(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        last_line = task_file.total_lines
        task = clock.find_task_at_line(task_file, last_line)
        assert task is not None
        assert task.title == "Support YAML front-matter"
        assert clock.find_task_at_line(task_file, last_line + 1) is None


# ---------------------------------------------------------------------------
# find_task_by_title
# ---------------------------------------------------------------------------


class TestFindTaskByTitle:
    def test_finds_exact_match(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        task = clock.find_task_by_title(task_file, "Add logging")
        assert task.status == model.Status.DONE

    def test_raises_not_found(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        with pytest.raises(clock.TaskNotFoundError):
            clock.find_task_by_title(task_file, "Nope")

    def test_raises_ambiguous_for_duplicate_titles(self) -> None:
        a = model.Task(
            level=1, status=model.Status.TODO, title="dup", source_line=1
        )
        b = model.Task(
            level=1, status=model.Status.TODO, title="dup", source_line=2
        )
        task_file = model.TaskFile(path=None, tasks=[a, b])
        with pytest.raises(clock.AmbiguousTaskError):
            clock.find_task_by_title(task_file, "dup")


# ---------------------------------------------------------------------------
# task_breadcrumb
# ---------------------------------------------------------------------------


class TestTaskBreadcrumb:
    def test_top_level_task_breadcrumb_is_just_its_title(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        task = next(t for t in task_file.walk() if t.title == "Add logging")
        assert clock.task_breadcrumb(task_file, task) == "Add logging"

    def test_nested_task_breadcrumb_includes_ancestors(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("nested.task.md", tmp_path)
        task_file = parser.parse_file(path)
        task = next(
            t for t in task_file.walk() if t.title == "Handle edge cases"
        )
        assert clock.task_breadcrumb(task_file, task) == (
            "Ship taskmd v0.1 > Write the parser > Handle edge cases"
        )

    def test_task_not_in_tree_falls_back_to_its_own_title(self) -> None:
        task_file = model.TaskFile(path=None, tasks=[])
        orphan = model.Task(level=1, status=model.Status.TODO, title="orphan")
        assert clock.task_breadcrumb(task_file, orphan) == "orphan"


# ---------------------------------------------------------------------------
# resolve_task
# ---------------------------------------------------------------------------


class TestResolveTask:
    def test_raises_if_neither_locator_given(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        with pytest.raises(ValueError):
            clock.resolve_task(task_file, None, None)

    def test_raises_if_both_locators_given(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        with pytest.raises(ValueError):
            clock.resolve_task(task_file, 1, "Add logging")

    def test_resolves_by_title(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        task = clock.resolve_task(task_file, None, "Add logging")
        assert task.title == "Add logging"

    def test_resolves_by_line(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        task = clock.resolve_task(task_file, 1, None)
        assert task.title == "Write the parser"

    def test_raises_task_not_found_for_bad_line(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        with pytest.raises(clock.TaskNotFoundError):
            clock.resolve_task(task_file, 9999, None)


# ---------------------------------------------------------------------------
# LineRewriter
# ---------------------------------------------------------------------------


class TestLineRewriter:
    def test_replace_line(self) -> None:
        rewriter = clock.LineRewriter("a\nb\nc\n")
        rewriter.replace_line(2, "B")
        assert rewriter.render() == "a\nB\nc\n"

    def test_insert_before(self) -> None:
        rewriter = clock.LineRewriter("a\nb\nc\n")
        rewriter.insert_before(2, ["x", "y"])
        assert rewriter.render() == "a\nx\ny\nb\nc\n"

    def test_insert_at_end_of_file(self) -> None:
        rewriter = clock.LineRewriter("a\nb\n")
        rewriter.insert_before(3, ["c"])
        assert rewriter.render() == "a\nb\nc\n"

    def test_render_empty_file(self) -> None:
        rewriter = clock.LineRewriter("")
        assert rewriter.render() == ""

    def test_write_atomic_creates_no_leftover_tmp_file(
        self, tmp_path: pathlib.Path
    ) -> None:
        target = tmp_path / "f.task.md"
        target.write_text("# TODO x\n")
        rewriter = clock.LineRewriter(target.read_text())
        rewriter.replace_line(1, "# DONE x")
        rewriter.write_atomic(target)
        assert target.read_text() == "# DONE x\n"
        assert not (tmp_path / "f.task.md.tmp").exists()

    def test_write_atomic_preserves_content_outside_edit(
        self, tmp_path: pathlib.Path
    ) -> None:
        target = tmp_path / "f.task.md"
        original = "# TODO a\nsome notes\nmore notes\n# DONE b\n"
        target.write_text(original)
        rewriter = clock.LineRewriter(target.read_text())
        rewriter.replace_line(1, "# DONE a")
        rewriter.write_atomic(target)
        assert target.read_text() == (
            "# DONE a\nsome notes\nmore notes\n# DONE b\n"
        )


# ---------------------------------------------------------------------------
# clock_start
# ---------------------------------------------------------------------------


class TestClockStart:
    def test_appends_open_clock_to_task_without_subtasks(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        now = _utc(2025, 7, 6, 14, 30)
        result = clock.clock_start(path, line=1, note="working", now=now)
        assert result.start == now
        assert result.end is None
        assert result.description == "working"

        task_file = parser.parse_file(path)
        task = task_file.tasks[0]
        assert len(task.clocks) == 1
        assert task.clocks[0].is_open()
        assert task.clocks[0].description == "working"

    def test_inserts_before_first_subtask_not_after_it(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("nested.task.md", tmp_path)
        now = _utc(2025, 7, 6, 10, 0)
        clock.clock_start(path, task_title="Write the parser", now=now)

        task_file = parser.parse_file(path)
        write_parser = next(
            t for t in task_file.walk() if t.title == "Write the parser"
        )
        assert len(write_parser.clocks) == 2  # one pre-existing + new
        assert write_parser.tasks[0].title == "Handle edge cases"
        assert task_file.warnings == [] or all(
            "unclosed" in str(w) for w in task_file.warnings
        )

    def test_appends_at_true_end_of_file_for_last_task(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        now = _utc(2025, 7, 6, 10, 0)
        clock.clock_start(
            path, task_title="Support YAML front-matter", now=now
        )
        task_file = parser.parse_file(path)
        last_task = task_file.tasks[-1]
        assert last_task.clocks[0].is_open()

    def test_no_note_gives_empty_description(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        now = _utc(2025, 7, 6, 10, 0)
        clock.clock_start(path, line=1, now=now)
        task_file = parser.parse_file(path)
        assert task_file.tasks[0].clocks[0].description == ""

    def test_clock_heading_depth_is_task_level_plus_one(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("nested.task.md", tmp_path)
        now = _utc(2025, 7, 6, 10, 0)
        clock.clock_start(path, task_title="Add logging", now=now)  # level 2
        text = path.read_text()
        assert "\n### CLOCK: " in text

    def test_strict_mode_rejects_second_open_session(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        with pytest.raises(clock.AlreadyOpenError):
            clock.clock_start(path, task_title="Write the parser")

    def test_lenient_mode_allows_stacking_open_sessions(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        config = parser.ParseConfig(strict=False)
        now = _utc(2025, 7, 6, 10, 0)
        clock.clock_start(
            path,
            config,
            task_title="Write the parser",
            now=now,
        )
        task_file = parser.parse_file(path, config=config)
        write_parser = next(
            t for t in task_file.walk() if t.title == "Write the parser"
        )
        open_count = sum(1 for c in write_parser.clocks if c.is_open())
        assert open_count == 2

    def test_uses_default_config_and_now_when_omitted(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        result = clock.clock_start(path, line=1)
        assert result.start.tzinfo is not None

    def test_raises_task_not_found_for_bad_line(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        with pytest.raises(clock.TaskNotFoundError):
            clock.clock_start(path, line=9999)

    def test_raises_task_not_found_for_bad_title(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        with pytest.raises(clock.TaskNotFoundError):
            clock.clock_start(path, task_title="Nope")


# ---------------------------------------------------------------------------
# clock_stop
# ---------------------------------------------------------------------------


class TestClockStop:
    def test_closes_by_line(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        stop_at = _utc(2025, 7, 6, 12, 0)
        result = clock.clock_stop(path, line=12, at=stop_at, note="closed")
        assert result.end == stop_at
        assert result.description == "closed"

        task_file = parser.parse_file(path)
        write_parser = task_file.tasks[0]
        assert all(not c.is_open() for c in write_parser.clocks)

    def test_closes_the_single_open_session_when_line_omitted(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        clock.clock_start(path, line=1, now=_utc(2025, 7, 6, 9, 0))
        clock.clock_stop(path, at=_utc(2025, 7, 6, 10, 0))
        task_file = parser.parse_file(path)
        assert task_file.tasks[0].clocks[0].end == _utc(2025, 7, 6, 10, 0)

    def test_no_note_keeps_original_description(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        clock.clock_start(
            path,
            line=1,
            note="original",
            now=_utc(2025, 7, 6, 9, 0),
        )
        clock.clock_stop(path, at=_utc(2025, 7, 6, 10, 0))
        task_file = parser.parse_file(path)
        assert task_file.tasks[0].clocks[0].description == "original"

    def test_note_overrides_description(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        clock.clock_start(
            path,
            line=1,
            note="original",
            now=_utc(2025, 7, 6, 9, 0),
        )
        clock.clock_stop(
            path,
            at=_utc(2025, 7, 6, 10, 0),
            note="replaced",
        )
        task_file = parser.parse_file(path)
        assert task_file.tasks[0].clocks[0].description == "replaced"

    def test_work_notes_below_heading_are_preserved(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        original_notes = parser.parse_file(path).tasks[0].clocks[0].work_notes
        clock.clock_stop(path, line=12, at=_utc(2025, 7, 6, 12, 0))
        task_file = parser.parse_file(path)
        assert task_file.tasks[0].clocks[0].work_notes == original_notes

    def test_raises_no_open_session_for_whole_file(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)  # nothing open
        with pytest.raises(clock.NoOpenSessionError):
            clock.clock_stop(path)

    def test_raises_no_open_session_for_specific_closed_task(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        with pytest.raises(clock.NoOpenSessionError):
            # "Add logging" (line 15) has only closed sessions.
            clock.clock_stop(path, line=15)

    def test_raises_task_not_found_for_bad_line(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        with pytest.raises(clock.TaskNotFoundError):
            clock.clock_stop(path, line=9999)

    def test_raises_ambiguous_with_all_open_sessions_listed(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        clock.clock_start(
            path,
            task_title="Add logging",
            now=_utc(2025, 7, 6, 9, 0),
        )
        with pytest.raises(clock.AmbiguousOpenSessionError) as exc_info:
            clock.clock_stop(path)
        titles = {task.title for task, _ in exc_info.value.open_sessions}
        assert titles == {"Write the parser", "Add logging"}

    def test_uses_default_config_and_at_when_omitted(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        clock.clock_start(path, line=1)
        result = clock.clock_stop(path)
        assert result.end is not None
        assert result.end.tzinfo is not None


# ---------------------------------------------------------------------------
# list_open_clocks
# ---------------------------------------------------------------------------


class TestListOpenClocks:
    def test_empty_when_nothing_open(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        assert clock.list_open_clocks(task_file) == []

    def test_finds_open_sessions_in_document_order(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        task_file = parser.parse_file(path)
        open_sessions = clock.list_open_clocks(task_file)
        assert [task.title for task, _ in open_sessions] == [
            "Write the parser",
        ]

    def test_finds_open_sessions_in_nested_tasks(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("nested.task.md", tmp_path)
        clock.clock_start(
            path,
            task_title="Document the CLI",
            now=_utc(2025, 7, 6, 9, 0),
        )
        task_file = parser.parse_file(path)
        open_sessions = clock.list_open_clocks(task_file)
        assert [task.title for task, _ in open_sessions] == [
            "Document the CLI",
        ]


# ---------------------------------------------------------------------------
# clock_status
# ---------------------------------------------------------------------------


class TestClockStatus:
    def test_file_wide_open(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        task_file = parser.parse_file(path)
        assert clock.clock_status(task_file) == 0

    def test_file_wide_closed(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        assert clock.clock_status(task_file) == 1

    def test_specific_task_open(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        task_file = parser.parse_file(path)
        assert clock.clock_status(task_file, line=1) == 0

    def test_specific_task_closed(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        task_file = parser.parse_file(path)
        assert clock.clock_status(task_file, line=15) == 1

    def test_specific_line_task_not_found(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        task_file = parser.parse_file(path)
        assert clock.clock_status(task_file, line=9999) == 2


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestCliClock:
    def test_start_and_stop_round_trip(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        exit_code = clock.main(
            ["clock", "start", str(path), "--line", "1", "--note", "cli"],
        )
        assert exit_code == 0
        assert "started clock" in capsys.readouterr().out

        exit_code = clock.main(["clock", "stop", str(path)])
        assert exit_code == 0
        assert "stopped clock" in capsys.readouterr().out

        task_file = parser.parse_file(path)
        assert not task_file.tasks[0].clocks[0].is_open()

    def test_start_by_task_title(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        exit_code = clock.main(
            ["clock", "start", str(path), "--task-title", "Add logging"],
        )
        assert exit_code == 0
        task_file = parser.parse_file(path)
        add_logging = next(
            t for t in task_file.walk() if t.title == "Add logging"
        )
        assert add_logging.clocks[-1].is_open()

    def test_start_already_open_strict_error(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        exit_code = clock.main(
            [
                "clock",
                "start",
                str(path),
                "--task-title",
                "Write the parser",
            ],
        )
        assert exit_code == 1
        assert "already has an open" in capsys.readouterr().err

    def test_stop_ambiguous_lists_sessions_and_exits_2(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        clock.main(
            ["clock", "start", str(path), "--task-title", "Add logging"],
        )
        capsys.readouterr()
        exit_code = clock.main(["clock", "stop", str(path)])
        assert exit_code == 2
        stderr = capsys.readouterr().err
        assert "Write the parser" in stderr
        assert "Add logging" in stderr

    def test_stop_no_open_session_error(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        exit_code = clock.main(["clock", "stop", str(path)])
        assert exit_code == 1
        assert "no open CLOCK" in capsys.readouterr().err

    def test_stop_with_explicit_time(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        clock.main(["clock", "start", str(path), "--line", "1"])
        capsys.readouterr()
        exit_code = clock.main(
            [
                "clock",
                "stop",
                str(path),
                "--time",
                "2025-07-06T18:00:00+00:00",
            ],
        )
        assert exit_code == 0
        task_file = parser.parse_file(path)
        assert task_file.tasks[0].clocks[0].end == _utc(2025, 7, 6, 18, 0)

    def test_stop_invalid_time_argument(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            clock.main(
                ["clock", "stop", str(path), "--time", "not-a-datetime"],
            )
        assert exc_info.value.code != 0

    def test_stop_time_without_timezone_is_rejected(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        with pytest.raises(SystemExit):
            clock.main(
                [
                    "clock",
                    "stop",
                    str(path),
                    "--time",
                    "2025-07-06T18:00:00",
                ],
            )

    def test_list_open_outputs_json(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        exit_code = clock.main(["clock", "list-open", str(path)])
        assert exit_code == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload[0]["task"] == "Write the parser"
        assert "line" in payload[0]
        assert "start" in payload[0]

    def test_status_open(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _copy_fixture("clocked.task.md", tmp_path)
        exit_code = clock.main(["clock", "status", str(path), "--line", "1"])
        assert exit_code == 0
        assert capsys.readouterr().out.strip() == "open"

    def test_status_closed(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        exit_code = clock.main(["clock", "status", str(path)])
        assert exit_code == 1
        assert capsys.readouterr().out.strip() == "closed"

    def test_status_task_not_found(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        exit_code = clock.main(
            ["clock", "status", str(path), "--line", "9999"],
        )
        assert exit_code == 2
        assert capsys.readouterr().out.strip() == "task not found"

    def test_lenient_flag_threaded_through(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = tmp_path / "lower.task.md"
        path.write_text("# todo lowercase\nsome text\n")
        exit_code = clock.main(
            ["clock", "start", str(path), "--line", "1", "--lenient"],
        )
        assert exit_code == 0

    def test_clock_with_no_subcommand_errors(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = clock.main(["clock"])
        assert exit_code == 1
        assert "choose a subcommand" in capsys.readouterr().err

    def test_nonexistent_file_start(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "missing.task.md"
        exit_code = clock.main(
            ["clock", "start", str(missing), "--line", "1"]
        )
        assert exit_code == 1
        assert "No such file" in capsys.readouterr().err

    def test_nonexistent_file_list_open(self, tmp_path: pathlib.Path) -> None:
        missing = tmp_path / "missing.task.md"
        exit_code = clock.main(["clock", "list-open", str(missing)])
        assert exit_code == 1

    def test_nonexistent_file_status(self, tmp_path: pathlib.Path) -> None:
        missing = tmp_path / "missing.task.md"
        exit_code = clock.main(["clock", "status", str(missing)])
        assert exit_code == 1

    def test_list_open_strict_parse_error(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bad_file = tmp_path / "bad.task.md"
        bad_file.write_text("# todo lowercase status\n")
        exit_code = clock.main(["clock", "list-open", str(bad_file)])
        assert exit_code == 1
        assert "taskmd clock list-open:" in capsys.readouterr().err

    def test_status_strict_parse_error(self, tmp_path: pathlib.Path) -> None:
        bad_file = tmp_path / "bad.task.md"
        bad_file.write_text("# todo lowercase status\n")
        exit_code = clock.main(["clock", "status", str(bad_file)])
        assert exit_code == 1

    def test_task_title_not_found_via_cli(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        exit_code = clock.main(
            ["clock", "start", str(path), "--task-title", "Nope"],
        )
        assert exit_code == 1
        assert "no task titled" in capsys.readouterr().err

    def test_line_and_task_title_mutually_exclusive(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        with pytest.raises(SystemExit):
            clock.main(
                [
                    "clock",
                    "start",
                    str(path),
                    "--line",
                    "1",
                    "--task-title",
                    "x",
                ],
            )

    def test_start_requires_a_locator(self, tmp_path: pathlib.Path) -> None:
        path = _copy_fixture("basic.task.md", tmp_path)
        with pytest.raises(SystemExit):
            clock.main(["clock", "start", str(path)])
