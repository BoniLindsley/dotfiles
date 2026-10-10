#!/usr/bin/env python3

# Standard libraries.
import datetime
import pathlib
import time

from typing import List

# External dependencies.
import pytest

# Internal modules.
from bonipy35.taskmd import errors
from bonipy35.taskmd import model
from bonipy35.taskmd import parser
from bonipy35.taskmd import recur

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def _fixture_path(name: str) -> pathlib.Path:
    return _FIXTURES_DIR / name


class TestParseConfigAllFieldsExplicit:
    def test_all_fields_explicit(self) -> None:
        tz = datetime.timezone.utc
        config = parser.ParseConfig(
            datetime_formats=["%Y-%m-%d"],
            local_timezone=tz,
            require_timezone=False,
            strict=False,
            warn_open_clocks=False,
            warnings=[],
        )
        assert config.datetime_formats == ["%Y-%m-%d"]
        assert config.local_timezone is tz
        assert config.require_timezone is False
        assert config.strict is False
        assert config.warn_open_clocks is False
        assert config.warnings == []


class TestScanLines:
    def test_body_lines_are_not_headings(self) -> None:
        tokens = parser.scan_lines("plain text\n    indented\n\n# TODO x\n")
        assert isinstance(tokens[0], parser.BodyLineToken)
        assert isinstance(tokens[1], parser.BodyLineToken)
        assert isinstance(tokens[2], parser.BodyLineToken)
        assert isinstance(tokens[3], parser.HeadingToken)

    def test_empty_text_produces_no_tokens(self) -> None:
        assert not parser.scan_lines("")

    def test_hash_without_space_is_not_a_heading(self) -> None:
        # "#no-space" should not be treated as a heading; it's common
        # in ordinary Markdown (e.g. a stray hashtag-like string).
        tokens = parser.scan_lines("#no-space\n")
        assert len(tokens) == 1
        assert isinstance(tokens[0], parser.BodyLineToken)

    def test_heading_depth(self) -> None:
        tokens = parser.scan_lines("# one\n## two\n###### six\n")

        heading_tokens = []  # type: List[parser.HeadingToken]
        for token in tokens:
            assert isinstance(token, parser.HeadingToken)
            heading_tokens.append(token)
        assert [token.depth for token in heading_tokens] == [1, 2, 6]
        assert [token.text for token in tokens] == ["one", "two", "six"]

    def test_line_numbers_are_one_based(self) -> None:
        tokens = parser.scan_lines("a\nb\n# TODO c\n")
        assert [t.line_number for t in tokens] == [1, 2, 3]

    def test_trailing_whitespace_is_stripped_from_heading_text(self) -> None:
        tokens = parser.scan_lines("# TODO trailing space   \n")
        assert tokens[0].text == "TODO trailing space"


class TestExtractTags:
    def test_no_tags(self) -> None:
        text, tags = parser.extract_tags("TODO plain title")
        assert text == "TODO plain title"
        assert tags == []

    def test_single_tag(self) -> None:
        text, tags = parser.extract_tags("TODO title :core:")
        assert text == "TODO title"
        assert tags == ["core"]

    def test_multiple_tags(self) -> None:
        text, tags = parser.extract_tags("TODO title :python:core:cli-tool:")
        assert text == "TODO title"
        assert tags == ["python", "core", "cli-tool"]

    def test_tag_characters_allow_digits_and_underscore(self) -> None:
        _, tags = parser.extract_tags("TODO title :v2:my_tag:")
        assert tags == ["v2", "my_tag"]

    def test_uppercase_is_not_a_valid_tag_block(self) -> None:
        text, tags = parser.extract_tags("TODO title :NotATag:")
        assert text == "TODO title :NotATag:"
        assert tags == []


class TestBuildTreeStrict:
    def test_all_status_keywords_recognized(self) -> None:
        text = "# TODO a\n# DONE b\n# DROP c\n# WAIT d\n"
        tf = parser.parse_string(text)
        assert [t.status.name for t in tf.tasks] == [
            "TODO",
            "DONE",
            "DROP",
            "WAIT",
        ]

    def test_description_block(self) -> None:
        text = "# TODO title\nFirst paragraph.\nSecond line.\n"
        tf = parser.parse_string(text)
        assert tf.tasks[0].description == "First paragraph.\nSecond line."

    def test_single_task(self) -> None:
        tf = parser.parse_string("# TODO Write the parser :python:core:\n")
        assert len(tf.tasks) == 1
        task = tf.tasks[0]
        assert task.status.name == "TODO"
        assert task.title == "Write the parser"
        assert task.tags == ["python", "core"]
        assert task.level == 1

    def test_subtask_nesting_by_depth(self) -> None:
        text = "# TODO parent\n## TODO child\n### TODO grandchild\n"
        tf = parser.parse_string(text)
        parent = tf.tasks[0]
        assert len(parent.tasks) == 1
        child = parent.tasks[0]
        assert child.title == "child"
        assert len(child.tasks) == 1
        assert child.tasks[0].title == "grandchild"

    def test_sibling_subtasks_at_same_depth(self) -> None:
        text = "# TODO parent\n## TODO first child\n## TODO second child\n"
        tf = parser.parse_string(text)
        assert [c.title for c in tf.tasks[0].tasks] == [
            "first child",
            "second child",
        ]

    def test_returning_to_shallower_depth_closes_deeper_tasks(self) -> None:
        text = "# TODO top one\n## TODO nested\n# TODO top two\n"
        tf = parser.parse_string(text)
        assert len(tf.tasks) == 2
        assert tf.tasks[0].tasks[0].title == "nested"
        assert tf.tasks[1].tasks == []

    def test_update_section_with_timestamp(self) -> None:
        text = (
            "# WAIT title\n"
            "### 2025-06-10T14:30+02:00 Progress update\n"
            "Work continued on the tokeniser.\n"
        )
        tf = parser.parse_string(text)
        update = tf.tasks[0].updates[0]
        assert update.title == "Progress update"
        assert update.body == "Work continued on the tokeniser."
        assert update.timestamp == datetime.datetime(
            2025,
            6,
            10,
            14,
            30,
            tzinfo=datetime.timezone(datetime.timedelta(hours=2)),
        )

    def test_update_section_without_timestamp(self) -> None:
        text = "# TODO title\n### Just a note\nSome body text.\n"
        tf = parser.parse_string(text)
        update = tf.tasks[0].updates[0]
        assert update.timestamp is None
        assert update.title == "Just a note"
        assert update.body == "Some body text."

    def test_closed_clock_entry(self) -> None:
        text = (
            "# TODO title\n"
            "### CLOCK: [2025-06-09T09:15:00+02:00]--[2025-06-09T11:00:00+02:00] work\n"
            "Notes about the session.\n"
        )
        tf = parser.parse_string(text)
        clock = tf.tasks[0].clocks[0]
        assert clock.description == "work"
        assert clock.work_notes == "Notes about the session."
        assert clock.is_open() is False
        assert clock.duration() == datetime.timedelta(hours=1, minutes=45)

    def test_open_clock_entry(self) -> None:
        text = (
            "# TODO title\n"
            "### CLOCK: [2025-06-11T09:00:00+02:00]-- Continuing\n"
        )
        tf = parser.parse_string(text)
        clock = tf.tasks[0].clocks[0]
        assert clock.end is None
        assert clock.is_open() is True
        assert clock.duration() == datetime.timedelta(0)

    def test_clock_entry_without_description(self) -> None:
        text = (
            "# DONE title\n"
            "### CLOCK: [2025-06-05T13:00:00+02:00]--[2025-06-05T14:30:00+02:00]\n"
        )
        tf = parser.parse_string(text)
        assert tf.tasks[0].clocks[0].description == ""

    def test_tags_not_inherited_in_storage(self) -> None:
        # SPEC.md section 4.4 / 3.1: tags are recorded only on the
        # declaring heading; inheritance is a reporting-time concern.
        text = "# TODO parent :core:\n## TODO child\n"
        tf = parser.parse_string(text)
        assert tf.tasks[0].tasks[0].tags == []


class TestBuildTreeStrictErrors:
    def test_lowercase_status_top_level_is_unknown_heading(self) -> None:
        with pytest.raises(errors.UnknownHeadingError):
            parser.parse_string("# todo lowercase\n")

    def test_clock_without_enclosing_task_is_error(self) -> None:
        with pytest.raises(errors.UnknownHeadingError):
            parser.parse_string(
                "### CLOCK: [2025-06-09T09:00:00+02:00]--[2025-06-09T10:00:00+02:00]\n"
            )

    def test_update_without_enclosing_task_is_error(self) -> None:
        with pytest.raises(errors.UnknownHeadingError):
            parser.parse_string("### Some update\n")

    def test_missing_timezone_on_clock_is_error(self) -> None:
        text = (
            "# TODO title\n"
            "### CLOCK: [2025-06-09T09:00]--[2025-06-09T10:00]\n"
        )
        with pytest.raises(errors.TimezoneError):
            parser.parse_string(text)

    def test_missing_timezone_on_update_is_error(self) -> None:
        text = "# TODO title\n### 2025-06-09T09:00 no tz update\n"
        with pytest.raises(errors.TimezoneError):
            parser.parse_string(text)

    def test_missing_double_dash_in_clock_is_error(self) -> None:
        text = "# TODO title\n### CLOCK: [2025-06-09T09:00:00+02:00] no dashes at all\n"
        with pytest.raises(errors.ClockFormatError):
            parser.parse_string(text)

    def test_unparseable_datetime_in_clock_is_error(self) -> None:
        text = "# TODO title\n### CLOCK: [not a date at all]--[2025-06-09T10:00:00+02:00]\n"
        with pytest.raises(errors.ClockFormatError):
            parser.parse_string(text)


class TestBuildTreeLenient:
    @pytest.fixture
    def lenient(self) -> parser.ParseConfig:
        return parser.ParseConfig(strict=False)

    def test_completely_malformed_clock_is_dropped_with_warning(
        self, lenient: parser.ParseConfig
    ) -> None:
        text = "# TODO title\n### CLOCK: not a valid clock line at all\n"
        tf = parser.parse_string(text, config=lenient)
        assert tf.tasks[0].clocks == []
        assert len(tf.warnings) == 1

    def test_lowercase_status_accepted(
        self, lenient: parser.ParseConfig
    ) -> None:
        tf = parser.parse_string("# todo lowercase\n", config=lenient)
        assert tf.tasks[0].status.name == "TODO"
        assert tf.tasks[0].title == "lowercase"

    def test_missing_double_dash_is_best_effort_parsed(
        self, lenient: parser.ParseConfig
    ) -> None:
        text = "# TODO title\n### CLOCK: [2025-06-09T09:00:00+02:00] stray text\n"
        tf = parser.parse_string(text, config=lenient)
        clock = tf.tasks[0].clocks[0]
        assert clock.end is None
        assert clock.description == "stray text"
        assert any("missing '--'" in str(w) for w in tf.warnings)

    def test_missing_timezone_on_clock_becomes_warning(
        self, lenient: parser.ParseConfig
    ) -> None:
        text = (
            "# TODO title\n"
            "### CLOCK: [2025-06-09T09:00]--[2025-06-09T10:00]\n"
        )
        tf = parser.parse_string(text, config=lenient)
        assert len(tf.tasks[0].clocks) == 1
        assert any("timezone" in str(w) for w in tf.warnings)

    def test_missing_timezone_uses_local_tz(
        self, lenient: parser.ParseConfig
    ) -> None:
        text = (
            "# TODO title\n"
            "### CLOCK: [2025-06-09T09:00]--[2025-06-09T10:00]\n"
        )
        tf = parser.parse_string(text, config=lenient)
        clock = tf.tasks[0].clocks[0]
        assert clock.start.tzinfo is not None
        assert clock.end is not None
        assert clock.end.tzinfo is not None

    def test_mixed_case_status_accepted(
        self, lenient: parser.ParseConfig
    ) -> None:
        tf = parser.parse_string("# ToDo mixed case\n", config=lenient)
        assert tf.tasks[0].status.name == "TODO"

    def test_unclosed_clock_is_silently_accepted_no_warning(
        self, lenient: parser.ParseConfig
    ) -> None:
        text = (
            "# TODO title\n"
            "### CLOCK: [2025-06-09T09:00:00+02:00]-- ongoing\n"
        )
        tf = parser.parse_string(text, config=lenient)
        # SPEC.md section 5: unclosed CLOCK: is "silently accepted" in
        # lenient mode -- i.e. no warning about it being open.
        assert not any("unclosed" in str(w) for w in tf.warnings)

    def test_unknown_top_level_heading_is_ignored_not_raised(
        self, lenient: parser.ParseConfig
    ) -> None:
        tf = parser.parse_string("### Some update\n", config=lenient)
        assert tf.tasks == []
        assert len(tf.warnings) == 1

    def test_unparseable_datetime_in_clock_is_error(
        self, lenient: parser.ParseConfig
    ) -> None:
        text = "# TODO title\n### CLOCK: [not a date at all]--[2025-06-09T10:00:00+02:00]\n"
        with pytest.raises(errors.ClockFormatError):
            parser.parse_string(text, config=lenient)


class TestUnclosedClockStrictWarning:
    def test_unclosed_clock_in_strict_mode_warns_but_does_not_raise(
        self,
    ) -> None:
        text = (
            "# TODO title\n"
            "### CLOCK: [2025-06-11T09:00:00+02:00]-- ongoing\n"
        )
        tf = parser.parse_string(text)  # strict by default
        assert len(tf.tasks[0].clocks) == 1
        assert any("unclosed" in str(w) for w in tf.warnings)


class TestTaskTotalDuration:
    def test_own_clocks_only(self) -> None:
        task = model.Task(level=1, status=model.Status.TODO, title="t")
        task.clocks.append(
            model.ClockEntry(
                start=datetime.datetime(
                    2025, 1, 1, 9, 0, tzinfo=datetime.timezone.utc
                ),
                end=datetime.datetime(
                    2025, 1, 1, 10, 30, tzinfo=datetime.timezone.utc
                ),
                description="",
                work_notes="",
            ),
        )
        assert task.total_duration() == datetime.timedelta(
            hours=1, minutes=30
        )

    def test_open_clocks_contribute_zero(self) -> None:
        task = model.Task(level=1, status=model.Status.TODO, title="t")
        task.clocks.append(
            model.ClockEntry(
                start=datetime.datetime(
                    2025, 1, 1, 9, 0, tzinfo=datetime.timezone.utc
                ),
                end=None,
                description="",
                work_notes="",
            ),
        )
        assert task.total_duration() == datetime.timedelta(0)

    def test_recursive_includes_subtasks(self) -> None:
        child = model.Task(level=2, status=model.Status.TODO, title="child")
        child.clocks.append(
            model.ClockEntry(
                start=datetime.datetime(
                    2025, 1, 1, 9, 0, tzinfo=datetime.timezone.utc
                ),
                end=datetime.datetime(
                    2025, 1, 1, 10, 0, tzinfo=datetime.timezone.utc
                ),
                description="",
                work_notes="",
            ),
        )
        parent = model.Task(
            level=1, status=model.Status.TODO, title="parent", tasks=[child]
        )
        parent.clocks.append(
            model.ClockEntry(
                start=datetime.datetime(
                    2025, 1, 1, 8, 0, tzinfo=datetime.timezone.utc
                ),
                end=datetime.datetime(
                    2025, 1, 1, 8, 30, tzinfo=datetime.timezone.utc
                ),
                description="",
                work_notes="",
            ),
        )
        assert parent.total_duration(recursive=True) == datetime.timedelta(
            hours=1,
            minutes=30,
        )
        assert parent.total_duration(recursive=False) == datetime.timedelta(
            minutes=30
        )


class TestEffectiveTags:
    def test_no_parent_tags(self) -> None:
        task = model.Task(
            level=1, status=model.Status.TODO, title="t", tags=["a", "b"]
        )
        assert task.effective_tags() == ["a", "b"]

    def test_with_parent_tags(self) -> None:
        task = model.Task(
            level=2, status=model.Status.TODO, title="t", tags=["b"]
        )
        assert task.effective_tags(["a"]) == ["a", "b"]

    def test_duplicates_removed_preserving_first_occurrence(self) -> None:
        task = model.Task(
            level=2, status=model.Status.TODO, title="t", tags=["a", "c"]
        )
        assert task.effective_tags(["a", "b"]) == ["a", "b", "c"]


class TestTaskWalkAndTaskFileWalk:
    def test_walk_depth_first(self) -> None:
        grandchild = model.Task(level=3, status=model.Status.TODO, title="gc")
        child = model.Task(
            level=2, status=model.Status.TODO, title="c", tasks=[grandchild]
        )
        parent = model.Task(
            level=1, status=model.Status.TODO, title="p", tasks=[child]
        )
        assert [t.title for t in parent.walk()] == ["p", "c", "gc"]

    def test_task_file_walk_across_top_level_tasks(self) -> None:
        a = model.Task(level=1, status=model.Status.TODO, title="a")
        b = model.Task(
            level=1,
            status=model.Status.TODO,
            title="b",
            tasks=[
                model.Task(level=2, status=model.Status.TODO, title="b1"),
            ],
        )
        tf = model.TaskFile(path=None, tasks=[a, b])
        assert [t.title for t in tf.walk()] == ["a", "b", "b1"]

    def test_events_defaults_to_empty_list(self) -> None:
        # Task.events already defaulted None -> []; TaskFile.events had
        # been missing the same guard.
        tf = model.TaskFile(path=None)
        assert tf.events == []

    def test_events_explicit_list_is_kept(self) -> None:
        event = model.Event(
            level=1,
            scheduled_start=datetime.datetime(
                2025,
                1,
                1,
                10,
                tzinfo=datetime.timezone.utc,
            ),
            scheduled_end=datetime.datetime(
                2025,
                1,
                1,
                11,
                tzinfo=datetime.timezone.utc,
            ),
            title="e",
        )
        tf = model.TaskFile(path=None, events=[event])
        assert tf.events == [event]


class TestTaskEventsContribution:
    def test_events_contribute_to_total_duration(self) -> None:
        # Task.events / Event is forward-declared for the Phase 6
        # scheduling extension; the parser doesn't populate it yet,
        # but Task.total_duration already knows how to fold it in.
        event = model.Event(
            level=2,
            scheduled_start=datetime.datetime(
                2025, 1, 1, 10, 0, tzinfo=datetime.timezone.utc
            ),
            scheduled_end=datetime.datetime(
                2025, 1, 1, 11, 0, tzinfo=datetime.timezone.utc
            ),
            title="Sprint planning",
        )
        event.clocks.append(
            model.ClockEntry(
                start=datetime.datetime(
                    2025, 1, 1, 10, 5, tzinfo=datetime.timezone.utc
                ),
                end=datetime.datetime(
                    2025, 1, 1, 10, 50, tzinfo=datetime.timezone.utc
                ),
                description="",
                work_notes="",
            ),
        )
        task = model.Task(
            level=1, status=model.Status.TODO, title="t", events=[event]
        )
        assert task.total_duration() == datetime.timedelta(minutes=45)


class TestConstructorDefaultBranches:
    """Every optional constructor field, passed explicitly (non-None),
    to flip the other side of each ``if x is None: x = default``
    branch that the rest of the suite only ever exercises one way."""

    def test_task_all_fields_explicit(self) -> None:
        child = model.Task(level=2, status=model.Status.TODO, title="c")
        event = model.Event(
            level=2,
            scheduled_start=datetime.datetime(
                2025,
                1,
                1,
                10,
                tzinfo=datetime.timezone.utc,
            ),
            scheduled_end=datetime.datetime(
                2025,
                1,
                1,
                11,
                tzinfo=datetime.timezone.utc,
            ),
            title="e",
        )
        task = model.Task(
            clocks=[],
            description="desc",
            events=[event],
            level=1,
            source_line=5,
            status=model.Status.TODO,
            tags=["x"],
            tasks=[child],
            title="t",
            updates=[],
        )
        assert task.events == [event]
        assert task.tasks == [child]
        assert task.source_line == 5

    def test_task_file_all_fields_explicit(self) -> None:
        task = model.Task(level=1, status=model.Status.TODO, title="t")
        tf = model.TaskFile(
            events=[],
            path=pathlib.Path("x.task.md"),
            tasks=[task],
            total_lines=10,
            warnings=[],
        )
        assert tf.tasks == [task]
        assert tf.total_lines == 10

    def test_event_all_fields_explicit(self) -> None:
        sub = model.Event(
            level=2,
            scheduled_start=datetime.datetime(
                2025,
                1,
                1,
                10,
                tzinfo=datetime.timezone.utc,
            ),
            scheduled_end=datetime.datetime(
                2025,
                1,
                1,
                11,
                tzinfo=datetime.timezone.utc,
            ),
            title="sub",
        )
        event = model.Event(
            clocks=[],
            description="agenda",
            level=1,
            recur=None,
            scheduled_start=datetime.datetime(
                2025,
                1,
                1,
                10,
                tzinfo=datetime.timezone.utc,
            ),
            scheduled_end=datetime.datetime(
                2025,
                1,
                1,
                11,
                tzinfo=datetime.timezone.utc,
            ),
            source_line=7,
            sub_events=[sub],
            tags=["meeting"],
            title="e",
            updates=[],
        )
        assert event.sub_events == [sub]
        assert event.source_line == 7


class TestRecurRule:
    def test_construction_keeps_fields(self) -> None:
        rule = recur.RecurRule(
            interval=1,
            prefix="+",
            raw="+1w",
            unit="w",
        )
        assert rule.interval == 1
        assert rule.prefix == "+"
        assert rule.raw == "+1w"
        assert rule.unit == "w"
        assert rule.until is None
        assert rule.weekdays is None

    def test_construction_with_weekdays_and_until(self) -> None:
        until = datetime.date(2026, 12, 31)
        rule = recur.RecurRule(
            interval=1,
            prefix="++",
            raw="++1m 2MON @2026-12-31",
            unit="m",
            until=until,
            weekdays=["2MON"],
        )
        assert rule.until == until
        assert rule.weekdays == ["2MON"]

    def test_occurrences_without_recur_in_range(self) -> None:
        start = datetime.datetime(
            2025, 1, 1, 10, tzinfo=datetime.timezone.utc
        )
        event = model.Event(
            level=1,
            scheduled_start=start,
            scheduled_end=start + datetime.timedelta(hours=1),
            title="e",
        )
        assert event.occurrences(
            datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
            datetime.datetime(2025, 2, 1, tzinfo=datetime.timezone.utc),
        ) == [start]

    def test_occurrences_without_recur_out_of_range(self) -> None:
        start = datetime.datetime(
            2025, 1, 1, 10, tzinfo=datetime.timezone.utc
        )
        event = model.Event(
            level=1,
            scheduled_start=start,
            scheduled_end=start + datetime.timedelta(hours=1),
            title="e",
        )
        assert not event.occurrences(
            datetime.datetime(2025, 3, 1, tzinfo=datetime.timezone.utc),
            datetime.datetime(2025, 4, 1, tzinfo=datetime.timezone.utc),
        )

    def test_occurrences_with_recur_delegates_to_recur_module(self) -> None:
        start = datetime.datetime(
            2025, 1, 1, 10, tzinfo=datetime.timezone.utc
        )
        event = model.Event(
            level=1,
            scheduled_start=start,
            scheduled_end=start + datetime.timedelta(hours=1),
            title="e",
            recur=recur.RecurRule(
                raw="+1w",
                prefix="+",
                interval=1,
                unit="w",
                weekdays=[],
                until=None,
            ),
        )
        result = event.occurrences(
            start,
            start + datetime.timedelta(days=14),
        )
        assert result == [
            start,
            start + datetime.timedelta(days=7),
            start + datetime.timedelta(days=14),
        ]


class TestEventHelpers:
    def _make_event(self) -> model.Event:
        return model.Event(
            level=1,
            scheduled_start=datetime.datetime(
                2025, 1, 1, 10, 0, tzinfo=datetime.timezone.utc
            ),
            scheduled_end=datetime.datetime(
                2025, 1, 1, 11, 0, tzinfo=datetime.timezone.utc
            ),
            title="Sprint planning",
        )

    def test_scheduled_duration(self) -> None:
        event = self._make_event()
        assert event.scheduled_duration() == datetime.timedelta(hours=1)

    def test_actual_duration_with_no_clocks(self) -> None:
        event = self._make_event()
        assert event.actual_duration() == datetime.timedelta(0)

    def test_actual_duration_and_divergence(self) -> None:
        event = self._make_event()
        event.clocks.append(
            model.ClockEntry(
                start=datetime.datetime(
                    2025, 1, 1, 10, 8, tzinfo=datetime.timezone.utc
                ),
                end=datetime.datetime(
                    2025, 1, 1, 10, 52, tzinfo=datetime.timezone.utc
                ),
                description="",
                work_notes="",
            ),
        )
        assert event.actual_duration() == datetime.timedelta(minutes=44)
        assert event.divergence() == datetime.timedelta(minutes=-16)


class TestClockEntry:
    def test_is_open(self) -> None:
        open_clock = model.ClockEntry(
            start=datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
            end=None,
            description="",
            work_notes="",
        )
        closed_clock = model.ClockEntry(
            start=datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(
                2025, 1, 1, 1, tzinfo=datetime.timezone.utc
            ),
            description="",
            work_notes="",
        )
        assert open_clock.is_open() is True
        assert closed_clock.is_open() is False


class TestFixtures:
    def test_basic_fixture_parses_cleanly(self) -> None:
        tf = parser.parse_file(_fixture_path("basic.task.md"))
        assert len(tf.tasks) == 4
        assert tf.tasks[0].status == model.Status.TODO
        assert tf.tasks[1].status == model.Status.DONE
        assert tf.tasks[2].status == model.Status.WAIT
        assert tf.tasks[3].status == model.Status.DROP
        assert tf.warnings == []

    def test_basic_fixture_tags(self) -> None:
        tf = parser.parse_file(_fixture_path("basic.task.md"))
        by_title = {t.title: t for t in tf.tasks}
        assert by_title["Write the parser"].tags == ["python", "core"]
        assert by_title["Add logging"].tags == ["core"]

    def test_clocked_fixture_has_one_open_session_warning(self) -> None:
        tf = parser.parse_file(_fixture_path("clocked.task.md"))
        assert len(tf.warnings) == 1
        assert "unclosed" in str(tf.warnings[0])

    def test_clocked_fixture_durations(self) -> None:
        tf = parser.parse_file(_fixture_path("clocked.task.md"))
        by_title = {t.title: t for t in tf.tasks}
        parser_task = by_title["Write the parser"]
        # Two closed sessions: 1h45m + 3h30m = 5h15m. The open third
        # session contributes zero.
        assert parser_task.total_duration() == datetime.timedelta(
            hours=5,
            minutes=15,
        )
        assert by_title[
            "Review open sessions across the team"
        ].total_duration() == (datetime.timedelta(0))

    def test_nested_fixture_depth_and_tag_inheritance(self) -> None:
        tf = parser.parse_file(_fixture_path("nested.task.md"))
        assert tf.warnings == []
        release = tf.tasks[0]
        assert release.title == "Ship taskmd v0.1"
        assert release.tags == ["release"]

        write_parser = release.tasks[0]
        assert write_parser.title == "Write the parser"
        assert write_parser.effective_tags(release.effective_tags()) == [
            "release",
            "python",
            "core",
        ]

        handle_edge_cases = write_parser.tasks[0]
        assert handle_edge_cases.tags == []
        assert handle_edge_cases.effective_tags(
            write_parser.effective_tags(release.effective_tags()),
        ) == ["release", "python", "core"]

    def test_nested_fixture_deepest_subtask(self) -> None:
        tf = parser.parse_file(_fixture_path("nested.task.md"))
        release = tf.tasks[0]
        docs = release.tasks[2]
        assert docs.title == "Write documentation"
        video = docs.tasks[1].tasks[0]
        assert video.title == "Add a video walkthrough"
        assert video.status == model.Status.DROP
        assert video.level == 4

    def test_all_fixtures_round_trip_through_parse_file(self) -> None:
        for name in ("basic.task.md", "clocked.task.md", "nested.task.md"):
            tf = parser.parse_file(_fixture_path(name))
            assert isinstance(tf, model.TaskFile)
            assert tf.path == _fixture_path(name)


# ---------------------------------------------------------------------------
# Errors module
# ---------------------------------------------------------------------------


class TestErrors:
    def test_parse_error_str_with_line_number(self) -> None:
        err = errors.ParseError("bad thing", line_number=5)
        assert str(err) == "line 5: bad thing"

    def test_parse_error_str_without_line_number(self) -> None:
        err = errors.ParseError("bad thing")
        assert str(err) == "bad thing"

    def test_all_specific_errors_are_parse_errors(self) -> None:
        for cls in (
            errors.ClockFormatError,
            errors.StatusError,
            errors.TimezoneError,
            errors.UnknownHeadingError,
            errors.RecurParseError,
        ):
            assert issubclass(cls, errors.ParseError)
            assert issubclass(cls, errors.TaskmdError)

    def test_parse_warning_is_a_taskmd_error_but_not_a_parse_error(
        self,
    ) -> None:
        assert issubclass(errors.ParseWarning, errors.TaskmdError)
        assert not issubclass(errors.ParseWarning, errors.ParseError)

    def test_parse_warning_str_without_line_number(self) -> None:
        assert str(errors.ParseWarning("heads up")) == "heads up"

    def test_parse_warning_str_with_line_number(self) -> None:
        assert (
            str(errors.ParseWarning("heads up", line_number=3))
            == "line 3: heads up"
        )


class TestParseStatusHeadingDefensiveGuard:
    def test_raises_status_error_if_called_directly_on_non_status_text(
        self,
    ) -> None:
        # build_tree never reaches this branch (it gates on
        # _matches_status first), but _parse_status_heading defends
        # against misuse if called directly.
        with pytest.raises(errors.StatusError):
            parser.parse_status_heading(
                "not a status keyword",
                config=parser.ParseConfig(),
                line_number=1,
            )


class TestSplitTimezoneSuffix:
    """`split_timezone_suffix` replaced reliance on `strptime`'s `%z`,
    which only understands colons / a literal `Z` from Python 3.7
    onward. These exercise it directly, independent of Python version."""

    def test_z_suffix_is_utc(self) -> None:
        naive_part, tzinfo_value = parser.split_timezone_suffix(
            "2025-06-10T12:30:00Z",
        )
        assert naive_part == "2025-06-10T12:30:00"
        assert tzinfo_value == datetime.timezone.utc

    def test_positive_offset_with_colon(self) -> None:
        naive_part, tzinfo_value = parser.split_timezone_suffix(
            "2025-06-09T09:15:00+02:00",
        )
        assert naive_part == "2025-06-09T09:15:00"
        assert tzinfo_value == datetime.timezone(datetime.timedelta(hours=2))

    def test_negative_offset_with_colon(self) -> None:
        naive_part, tzinfo_value = parser.split_timezone_suffix(
            "2025-06-09T09:15:00-05:00",
        )
        assert naive_part == "2025-06-09T09:15:00"
        assert tzinfo_value == datetime.timezone(datetime.timedelta(hours=-5))

    def test_offset_without_colon(self) -> None:
        naive_part, tzinfo_value = parser.split_timezone_suffix(
            "2025-06-09T09:15:00+0200",
        )
        assert naive_part == "2025-06-09T09:15:00"
        assert tzinfo_value == datetime.timezone(datetime.timedelta(hours=2))

    def test_hour_only_offset(self) -> None:
        naive_part, tzinfo_value = parser.split_timezone_suffix(
            "2025-06-09T09:15:00+02",
        )
        assert naive_part == "2025-06-09T09:15:00"
        assert tzinfo_value == datetime.timezone(datetime.timedelta(hours=2))

    def test_no_timezone_suffix(self) -> None:
        naive_part, tzinfo_value = parser.split_timezone_suffix(
            "2025-06-09T09:15:00",
        )
        assert naive_part == "2025-06-09T09:15:00"
        assert tzinfo_value is None

    def test_date_internal_dashes_are_not_mistaken_for_a_timezone(
        self,
    ) -> None:
        # The date "2025-06-09" has internal dashes that could be
        # confused with a timezone sign if the pattern weren't
        # anchored to the end of the string.
        naive_part, tzinfo_value = parser.split_timezone_suffix(
            "2025-06-09T09:15:00",
        )
        assert naive_part == "2025-06-09T09:15:00"
        assert tzinfo_value is None

    def test_negative_offset_round_trips_through_parse_datetime(
        self,
    ) -> None:
        config = parser.ParseConfig()
        parsed = parser.parse_datetime(
            "2025-06-09T09:15:00-05:00",
            config=config,
            line_number=1,
        )
        assert parsed.utcoffset() == -datetime.timedelta(hours=5)


class TestGetLocalTimezone:
    def test_returns_a_fixed_offset_timezone(self) -> None:
        local_tz = parser.get_local_timezone()
        assert isinstance(local_tz, datetime.timezone)

    def test_used_as_parse_config_default(self) -> None:
        config = parser.ParseConfig()
        assert isinstance(config.local_timezone, datetime.timezone)

    def test_dst_branch_uses_altzone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_localtime = type(
            "FakeStructTime",
            (),
            {"tm_isdst": 1},
        )()
        monkeypatch.setattr(time, "daylight", 1)
        monkeypatch.setattr(time, "altzone", -3600)
        monkeypatch.setattr(time, "localtime", lambda: fake_localtime)
        local_tz = parser.get_local_timezone()
        assert local_tz.utcoffset(None) == datetime.timedelta(hours=1)

    def test_non_dst_branch_uses_timezone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_localtime = type(
            "FakeStructTime",
            (),
            {"tm_isdst": 0},
        )()
        monkeypatch.setattr(time, "daylight", 0)
        monkeypatch.setattr(time, "timezone", 0)
        monkeypatch.setattr(time, "localtime", lambda: fake_localtime)
        local_tz = parser.get_local_timezone()
        assert local_tz.utcoffset(None) == datetime.timedelta(0)


class TestEventParsing:
    def test_top_level_event(self) -> None:
        task_file = parser.parse_string(
            "# EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] "
            "Sprint planning :meeting:\n"
        )
        assert not task_file.tasks
        assert len(task_file.events) == 1
        event = task_file.events[0]
        assert event.title == "Sprint planning"
        assert event.tags == ["meeting"]
        assert event.scheduled_start == datetime.datetime(
            2025,
            9,
            1,
            10,
            tzinfo=datetime.timezone(datetime.timedelta(hours=1)),
        )
        assert event.scheduled_duration() == datetime.timedelta(hours=1)

    def test_event_nested_under_task(self) -> None:
        task_file = parser.parse_string(
            "# TODO Implement the parser :core:\n"
            "## EVENT [2025-09-04T13:00+01:00--2025-09-04T15:00+01:00] "
            "Focus session\n"
            "### CLOCK: [2025-09-04T13:05+01:00]--"
            "[2025-09-04T14:45+01:00]\n"
        )
        task = task_file.tasks[0]
        assert len(task.events) == 1
        event = task.events[0]
        assert event.clocks[0].duration() == datetime.timedelta(
            hours=1, minutes=40
        )
        assert task.total_duration() == datetime.timedelta(
            hours=1, minutes=40
        )

    def test_event_with_recur_and_tags(self) -> None:
        task_file = parser.parse_string(
            "# EVENT [2025-09-03T09:00+01:00--2025-09-03T11:00+01:00] "
            "Focus: parser work RECUR +1w :block:\n"
        )
        event = task_file.events[0]
        assert event.title == "Focus: parser work"
        assert event.tags == ["block"]
        assert event.recur is not None
        assert event.recur.raw == "+1w"

    def test_sub_events(self) -> None:
        task_file = parser.parse_string(
            "# EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] "
            "Sprint planning\n"
            "## EVENT [2025-09-01T10:00+01:00--2025-09-01T10:15+01:00] "
            "Velocity review\n"
        )
        event = task_file.events[0]
        assert len(event.sub_events) == 1
        assert event.sub_events[0].title == "Velocity review"
        assert list(event.walk()) == [event, event.sub_events[0]]
        assert list(task_file.walk_events()) == [
            event,
            event.sub_events[0],
        ]

    def test_event_description_and_update(self) -> None:
        task_file = parser.parse_string(
            "# EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] "
            "Sprint planning\n"
            "Agenda: velocity review.\n"
            "\n"
            "### 2025-09-01T12:00+01:00 Follow-up\n"
            "Notes here.\n"
        )
        event = task_file.events[0]
        assert event.description == "Agenda: velocity review."
        assert event.updates[0].title == "Follow-up"
        assert event.updates[0].body == "Notes here."

    def test_malformed_span_strict_raises(self) -> None:
        with pytest.raises(errors.ClockFormatError):
            parser.parse_string("# EVENT [2025-09-01T10:00+01:00] Bad span\n")

    def test_malformed_span_lenient_warns(self) -> None:
        config = parser.ParseConfig(strict=False)
        task_file = parser.parse_string(
            "# EVENT [2025-09-01T10:00+01:00] Bad span\n",
            config=config,
        )
        assert task_file.warnings

    def test_invalid_recur_strict_raises(self) -> None:
        with pytest.raises(errors.RecurParseError):
            parser.parse_string(
                "# EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] "
                "Sprint planning RECUR bogus\n"
            )

    def test_invalid_recur_lenient_warns(self) -> None:
        config = parser.ParseConfig(strict=False)
        task_file = parser.parse_string(
            "# EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] "
            "Sprint planning RECUR bogus\n",
            config=config,
        )
        event = task_file.events[0]
        assert event.recur is not None
        assert event.recur.raw == "bogus"
        assert task_file.warnings

    def test_task_cannot_nest_inside_event_strict_raises(self) -> None:
        with pytest.raises(errors.UnknownHeadingError):
            parser.parse_string(
                "# EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] "
                "Sprint planning\n"
                "## TODO Nested task\n"
            )

    def test_task_cannot_nest_inside_event_lenient_warns(self) -> None:
        config = parser.ParseConfig(strict=False)
        task_file = parser.parse_string(
            "# EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] "
            "Sprint planning\n"
            "## TODO Nested task\n",
            config=config,
        )
        assert task_file.warnings
        assert not task_file.events[0].sub_events

    def test_lenient_case_insensitive_event_and_recur(self) -> None:
        config = parser.ParseConfig(strict=False)
        task_file = parser.parse_string(
            "# event [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] "
            "Sprint planning recur +1w\n",
            config=config,
        )
        event = task_file.events[0]
        assert event.title == "Sprint planning"
        assert event.recur is not None

    def test_open_clock_under_event_warns(self) -> None:
        config = parser.ParseConfig(strict=True)
        task_file = parser.parse_string(
            "# EVENT [2025-09-01T10:00+01:00--2025-09-01T11:00+01:00] "
            "Sprint planning\n"
            "### CLOCK: [2025-09-01T10:00+01:00]--\n",
            config=config,
        )
        assert any("event" in str(warning) for warning in task_file.warnings)
