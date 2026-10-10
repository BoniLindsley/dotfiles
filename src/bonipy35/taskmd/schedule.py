#!/usr/bin/env python3

"""`taskmd schedule` -- agenda, conflict, and summary views over
`EVENT` entries (`SPEC.md` section 7). Operates on already-parsed
`model.TaskFile` objects; the CLI glue (argument parsing, file
discovery, printing) lives at the bottom of this module, mirroring
the `report.py` / `clock.py` split used elsewhere in this package.
"""

# Standard libraries.
import argparse
import datetime
import json
import logging
import sys
import typing

from typing import Dict, List, Tuple, Union

# Internal modules.
from .. import datetime_ext
from .. import logging_ext

from . import cli_args
from . import errors
from . import model
from . import parser
from . import report

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Collecting and filtering events
# ---------------------------------------------------------------------------


class ScheduleFilter:
    def __init__(
        self,
        *args: typing.Any,
        include_inherited_tags: Union[None, bool] = True,
        statuses: Union[None, List[model.Status]] = None,
        tags: Union[None, List[str]] = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.include_inherited_tags = (
            True if include_inherited_tags is None else include_inherited_tags
        )
        self.statuses = [] if statuses is None else statuses
        self.tags = [] if tags is None else tags


class EventMatch:
    """One `Event`, together with the tag set it should be filtered
    on (its own tags plus any inherited from an enclosing task or
    event) and the nearest enclosing `Task`, if any."""

    def __init__(
        self,
        *,
        event: model.Event,
        tags: List[str],
        task: Union[None, model.Task]
    ) -> None:
        self.event = event
        self.tags = tags
        self.task = task


def _combine_tags(parent_tags: List[str], own_tags: List[str]) -> List[str]:
    seen = set()
    combined = []
    for tag in list(parent_tags) + list(own_tags):
        if tag not in seen:
            seen.add(tag)
            combined.append(tag)
    return combined


def _walk_event(
    event: model.Event, parent_tags: List[str], task: Union[None, model.Task]
) -> "typing.Iterator[EventMatch]":
    tags = _combine_tags(parent_tags, event.tags)
    yield EventMatch(event=event, tags=tags, task=task)
    for sub_event in event.sub_events:
        yield from _walk_event(sub_event, tags, task)


def _walk_tasks_with_tags(
    tasks: List[model.Task], parent_tags: List[str]
) -> "typing.Iterator[Tuple[model.Task, List[str]]]":
    for task in tasks:
        own_tags = task.effective_tags(parent_tags)
        yield task, own_tags
        yield from _walk_tasks_with_tags(task.tasks, own_tags)


def iter_events(task_file: model.TaskFile) -> "typing.Iterator[EventMatch]":
    """Every `Event` reachable from `task_file`, paired with its
    (inherited) tag set and nearest enclosing task, if any."""
    for event in task_file.events:
        yield from _walk_event(event, [], None)
    for task, tags in _walk_tasks_with_tags(task_file.tasks, []):
        for event in task.events:
            yield from _walk_event(event, tags, task)


def matches_event_filter(
    match: EventMatch, filter_: Union[None, ScheduleFilter]
) -> bool:
    if filter_ is None:
        return True
    if filter_.tags:
        tags_to_check = (
            match.tags if filter_.include_inherited_tags else match.event.tags
        )
        if not set(filter_.tags).issubset(set(tags_to_check)):
            return False
    if filter_.statuses and (
        match.task is None or match.task.status not in filter_.statuses
    ):
        return False
    return True


# ---------------------------------------------------------------------------
# Occurrence expansion within a window
# ---------------------------------------------------------------------------


class Occurrence:
    def __init__(
        self,
        *,
        end: datetime.datetime,
        event: model.Event,
        is_anchor: bool,
        start: datetime.datetime,
        tags: List[str]
    ) -> None:
        self.end = end
        self.event = event
        self.is_anchor = is_anchor
        self.start = start
        self.tags = tags


def expand_occurrences(
    match: EventMatch,
    window_from: datetime.datetime,
    window_to: datetime.datetime,
) -> "typing.Iterator[Occurrence]":
    event = match.event
    duration = event.scheduled_duration()
    for start in event.occurrences(window_from, window_to):
        yield Occurrence(
            event=event,
            start=start,
            end=start + duration,
            is_anchor=(start == event.scheduled_start),
            tags=match.tags,
        )


def collect_occurrences(
    task_files: List[model.TaskFile],
    window_from: datetime.datetime,
    window_to: datetime.datetime,
    filter_: Union[None, ScheduleFilter] = None,
) -> List[Occurrence]:
    occurrences = []  # type: List[Occurrence]
    for task_file in task_files:
        for match in iter_events(task_file):
            if not matches_event_filter(match, filter_):
                continue
            occurrences.extend(
                expand_occurrences(match, window_from, window_to)
            )
    occurrences.sort(key=lambda occurrence: occurrence.start)
    return occurrences


# ---------------------------------------------------------------------------
# `schedule show`
# ---------------------------------------------------------------------------


def format_divergence(event: model.Event) -> Union[None, str]:
    """`[+8m late, -8m short]`-style annotation, derived by comparing
    the earliest/latest `CLOCK:` timestamps against the scheduled
    span. Returns `None` when there is nothing to report (no closed
    clocks, or actual matches scheduled exactly)."""
    closed = [clock for clock in event.clocks if clock.end is not None]
    if not closed:
        return None
    earliest_start = min(clock.start for clock in closed)
    latest_end = max(
        typing.cast(datetime.datetime, clock.end) for clock in closed
    )
    late = earliest_start - event.scheduled_start
    short = event.scheduled_end - latest_end

    parts = []
    if late.total_seconds() > 0:
        parts.append("+{0} late".format(report.format_duration(late)))
    if short.total_seconds() > 0:
        parts.append("-{0} short".format(report.format_duration(short)))
    if not parts:
        return None
    return "[{0}]".format(", ".join(parts))


def render_agenda_text(occurrences: List[Occurrence]) -> str:
    if not occurrences:
        return "(no events in range)"

    lines = []  # type: List[str]
    current_day = None  # type: Union[None, datetime.date]
    for occurrence in occurrences:
        day = occurrence.start.date()
        if day != current_day:
            if current_day is not None:
                lines.append("")
            lines.append(occurrence.start.strftime("%a %Y-%m-%d"))
            current_day = day

        title = occurrence.event.title
        if not occurrence.is_anchor:
            title += " (recurring)"
        span = "{0}\u2013{1}".format(
            occurrence.start.strftime("%H:%M"),
            occurrence.end.strftime("%H:%M"),
        )
        tags = "".join(":{0}:".format(tag) for tag in occurrence.tags)
        pieces = ["  {0}  {1}".format(span, title)]
        if tags:
            pieces.append(tags)
        if occurrence.is_anchor:
            divergence = format_divergence(occurrence.event)
            if divergence is not None:
                pieces.append(divergence)
        lines.append("  ".join(pieces))

    return "\n".join(lines)


def occurrence_to_dict(occurrence: Occurrence) -> Dict[str, typing.Any]:
    return {
        "title": occurrence.event.title,
        "start": occurrence.start.isoformat(),
        "end": occurrence.end.isoformat(),
        "tags": list(occurrence.tags),
        "recurring": not occurrence.is_anchor,
        "divergence": (
            format_divergence(occurrence.event)
            if occurrence.is_anchor
            else None
        ),
    }


def render_agenda_json(occurrences: List[Occurrence]) -> str:
    payload = [occurrence_to_dict(occurrence) for occurrence in occurrences]
    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# `schedule conflicts`
# ---------------------------------------------------------------------------


class Conflict:
    def __init__(
        self,
        *,
        first: Occurrence,
        overlap: datetime.timedelta,
        second: Occurrence
    ) -> None:
        self.first = first
        self.overlap = overlap
        self.second = second


def find_conflicts(occurrences: List[Occurrence]) -> List[Conflict]:
    """`occurrences` must already be sorted by start time (as
    returned by `collect_occurrences`)."""
    conflicts = []
    for index, first in enumerate(occurrences):
        for second in occurrences[index + 1 :]:
            if second.start >= first.end:
                break
            overlap_start = max(first.start, second.start)
            overlap_end = min(first.end, second.end)
            if overlap_end > overlap_start:
                conflicts.append(
                    Conflict(
                        first=first,
                        second=second,
                        overlap=overlap_end - overlap_start,
                    )
                )
    return conflicts


def render_conflicts_text(conflicts: List[Conflict]) -> str:
    if not conflicts:
        return "(no conflicts in range)"
    lines = []
    for conflict in conflicts:
        lines.append(
            "{0} ({1}--{2}) overlaps {3} ({4}--{5}) by {6}".format(
                conflict.first.event.title,
                datetime_ext.format_datetime(
                    conflict.first.start, minutes=True
                ),
                datetime_ext.format_datetime(
                    conflict.first.end, minutes=True
                ),
                conflict.second.event.title,
                datetime_ext.format_datetime(
                    conflict.second.start, minutes=True
                ),
                datetime_ext.format_datetime(
                    conflict.second.end, minutes=True
                ),
                report.format_duration(conflict.overlap),
            ),
        )
    return "\n".join(lines)


def render_conflicts_json(conflicts: List[Conflict]) -> str:
    payload = [
        {
            "first": occurrence_to_dict(conflict.first),
            "second": occurrence_to_dict(conflict.second),
            "overlap_seconds": conflict.overlap.total_seconds(),
            "overlap": report.format_duration(conflict.overlap),
        }
        for conflict in conflicts
    ]
    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# `schedule summary`
# ---------------------------------------------------------------------------


class SummaryRow:
    def __init__(self) -> None:
        self.count = 0
        self.actual = datetime.timedelta(0)
        self.scheduled = datetime.timedelta(0)

    def delta(self) -> datetime.timedelta:
        return self.actual - self.scheduled


def _group_keys(
    group_by: str, occurrence: Occurrence, match_task: Union[None, model.Task]
) -> List[str]:
    if group_by == "tag":
        return list(occurrence.tags) or ["(untagged)"]
    if group_by == "task":
        return [match_task.title if match_task is not None else "(no task)"]
    if group_by == "day":
        return [occurrence.start.date().isoformat()]
    if group_by == "week":
        year, week, _ = occurrence.start.isocalendar()
        return ["{0}-W{1:02d}".format(year, week)]
    raise ValueError("unknown group_by: {0!r}".format(group_by))


def summarize(
    task_files: List[model.TaskFile],
    window_from: datetime.datetime,
    window_to: datetime.datetime,
    *,
    filter_: Union[None, ScheduleFilter] = None,
    group_by: str = "tag"
) -> "Dict[str, SummaryRow]":
    groups = {}  # type: Dict[str, SummaryRow]
    for task_file in task_files:
        for match in iter_events(task_file):
            if not matches_event_filter(match, filter_):
                continue
            for occurrence in expand_occurrences(
                match, window_from, window_to
            ):
                actual = (
                    occurrence.event.actual_duration()
                    if occurrence.is_anchor
                    else datetime.timedelta(0)
                )
                scheduled = occurrence.end - occurrence.start
                for key in _group_keys(group_by, occurrence, match.task):
                    row = groups.setdefault(key, SummaryRow())
                    row.count += 1
                    row.actual += actual
                    row.scheduled += scheduled
    return groups


def render_summary_text(groups: "Dict[str, SummaryRow]") -> str:
    if not groups:
        return "(no events in range)"

    lines = []
    total = SummaryRow()
    for key in sorted(groups):
        row = groups[key]
        total.count += row.count
        total.actual += row.actual
        total.scheduled += row.scheduled
        lines.append(
            "  {0:<12}{1:>3} events{2:>13} scheduled{3:>12} "
            "actual{4:>10} total".format(
                key + ":",
                row.count,
                report.format_duration(row.scheduled),
                report.format_duration(row.actual),
                report.format_duration(row.delta()),
            ),
        )
    lines.append("-" * 60)
    lines.append(
        "  {0:<12}{1:>3} events{2:>13} scheduled{3:>12} "
        "actual{4:>10} total".format(
            "Total:",
            total.count,
            report.format_duration(total.scheduled),
            report.format_duration(total.actual),
            report.format_duration(total.delta()),
        ),
    )
    return "\n".join(lines)


def render_summary_json(groups: "Dict[str, SummaryRow]") -> str:
    payload = {
        key: {
            "count": row.count,
            "scheduled_seconds": row.scheduled.total_seconds(),
            "actual_seconds": row.actual.total_seconds(),
            "delta_seconds": row.delta().total_seconds(),
        }
        for key, row in groups.items()
    }
    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# CLI glue
# ---------------------------------------------------------------------------


def add_filter_flags(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument(
        "--tag",
        action="append",
        dest="tag",
        metavar="TAG",
        help="only include events carrying TAG (repeatable)",
    )
    cli_args.add_status_flag(
        subparser,
        help_text="only include events under a task with this status (repeatable)",
    )


def _load_task_files(
    args: argparse.Namespace, config: parser.ParseConfig
) -> Union[List[model.TaskFile], int]:
    """Returns the parsed files, or an exit code on failure."""
    paths = report.discover_paths(
        files=(args.file or []) + list(args.paths),
        directory=args.dir,
        depth=args.depth,
    )
    if not paths:
        print(
            "taskmd schedule: no input files given (use --file or --dir)",
            file=sys.stderr,
        )
        return 1

    task_files = []
    for path in paths:
        try:
            task_files.append(parser.parse_file(path, config=config))
        except errors.ParseError as error:
            print(
                "taskmd schedule: {0}: {1}".format(path, error),
                file=sys.stderr,
            )
            return 1
        except OSError as error:
            print(
                "taskmd schedule: {0}: {1}".format(
                    path, error.strerror or error
                ),
                file=sys.stderr,
            )
            return 1
    return task_files


def _window(
    args: argparse.Namespace,
) -> Tuple[datetime.datetime, datetime.datetime]:
    local_tz = parser.get_local_timezone()
    today = datetime.datetime.now(local_tz)
    from_date = args.from_date or today.date()
    to_date = args.to_date or (from_date + datetime.timedelta(days=args.days))
    window_from = datetime.datetime.combine(
        from_date, datetime.time.min
    ).replace(tzinfo=local_tz)
    window_to = datetime.datetime.combine(to_date, datetime.time.max).replace(
        tzinfo=local_tz
    )
    return window_from, window_to


def _filter_from_args(args: argparse.Namespace) -> ScheduleFilter:
    return ScheduleFilter(
        tags=args.tag or [],
        statuses=[
            model.Status[status.upper()] for status in args.status or []
        ],
    )


def run_schedule_show(args: argparse.Namespace) -> int:
    config = parser.ParseConfig(strict=not args.lenient)
    task_files = _load_task_files(args, config)
    if isinstance(task_files, int):
        return task_files

    window_from, window_to = _window(args)
    filter_ = _filter_from_args(args)
    occurrences = collect_occurrences(
        task_files, window_from, window_to, filter_
    )

    if args.format == "json":
        print(render_agenda_json(occurrences))
    else:
        print(render_agenda_text(occurrences))
    return 0


def run_schedule_conflicts(args: argparse.Namespace) -> int:
    config = parser.ParseConfig(strict=not args.lenient)
    task_files = _load_task_files(args, config)
    if isinstance(task_files, int):
        return task_files

    window_from, window_to = _window(args)
    filter_ = _filter_from_args(args)
    occurrences = collect_occurrences(
        task_files, window_from, window_to, filter_
    )
    conflicts = find_conflicts(occurrences)

    if args.format == "json":
        print(render_conflicts_json(conflicts))
    else:
        print(render_conflicts_text(conflicts))
    return 2 if conflicts else 0


def run_schedule_summary(args: argparse.Namespace) -> int:
    config = parser.ParseConfig(strict=not args.lenient)
    task_files = _load_task_files(args, config)
    if isinstance(task_files, int):
        return task_files

    window_from, window_to = _window(args)
    filter_ = _filter_from_args(args)
    groups = summarize(
        task_files,
        window_from,
        window_to,
        filter_=filter_,
        group_by=args.group_by,
    )

    if args.format == "json":
        print(render_summary_json(groups))
    else:
        print(render_summary_text(groups))
    return 0


def run(args: argparse.Namespace) -> int:
    if args.schedule_command is None:
        print(
            "taskmd schedule: choose a subcommand "
            "(show/conflicts/summary)",
            file=sys.stderr,
        )
        return 1
    handler = {
        "show": run_schedule_show,
        "conflicts": run_schedule_conflicts,
        "summary": run_schedule_summary,
    }[args.schedule_command]
    return handler(args)


def main(argv: Union[None, List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    argument_parser = argparse.ArgumentParser(
        description="agenda/conflict/summary views over EVENT entries",
    )
    logging_ext.add_verbose_flag(argument_parser)

    schedule_subparsers = argument_parser.add_subparsers(
        dest="schedule_command"
    )

    show_parser = schedule_subparsers.add_parser(
        "show", help="show upcoming events as a chronological agenda"
    )
    cli_args.add_input_flags(show_parser)
    add_filter_flags(show_parser)
    cli_args.add_mode_flags(show_parser)
    show_parser.add_argument(
        "--from",
        dest="from_date",
        type=cli_args.parse_iso_date,
        metavar="DATE",
    )
    show_parser.add_argument(
        "--to", dest="to_date", type=cli_args.parse_iso_date, metavar="DATE"
    )
    show_parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="window size in days when --to is omitted (default: 14)",
    )
    show_parser.add_argument(
        "--format", choices=("text", "json"), default="text"
    )

    conflicts_parser = schedule_subparsers.add_parser(
        "conflicts", help="report scheduling overlaps within a window"
    )
    cli_args.add_input_flags(conflicts_parser)
    add_filter_flags(conflicts_parser)
    cli_args.add_mode_flags(conflicts_parser)
    conflicts_parser.add_argument(
        "--from",
        dest="from_date",
        type=cli_args.parse_iso_date,
        metavar="DATE",
    )
    conflicts_parser.add_argument(
        "--to", dest="to_date", type=cli_args.parse_iso_date, metavar="DATE"
    )
    conflicts_parser.add_argument("--days", type=int, default=14)
    conflicts_parser.add_argument(
        "--format", choices=("text", "json"), default="text"
    )

    summary_parser = schedule_subparsers.add_parser(
        "summary", help="aggregate scheduled/actual time over a period"
    )
    cli_args.add_input_flags(summary_parser)
    add_filter_flags(summary_parser)
    cli_args.add_mode_flags(summary_parser)
    summary_parser.add_argument(
        "--from",
        dest="from_date",
        type=cli_args.parse_iso_date,
        metavar="DATE",
    )
    summary_parser.add_argument(
        "--to", dest="to_date", type=cli_args.parse_iso_date, metavar="DATE"
    )
    summary_parser.add_argument("--days", type=int, default=30)
    summary_parser.add_argument(
        "--group-by",
        dest="group_by",
        choices=("tag", "task", "day", "week"),
        default="tag",
    )
    summary_parser.add_argument(
        "--format", choices=("text", "json"), default="text"
    )

    arguments = argument_parser.parse_args(argv[1:])
    return run(arguments)


if __name__ == "__main__":
    sys.exit(main())
