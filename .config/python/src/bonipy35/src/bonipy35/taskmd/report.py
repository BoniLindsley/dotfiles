#!/usr/bin/env python3

# Standard libraries.
import argparse
import copy
import csv
import datetime
import io
import json
import logging
import os
import pathlib
import sys
import typing

from typing import Dict, List, Union

# Internal modules.
from .. import datetime_ext
from .. import logging_ext
from .. import xdg

from . import cli_args
from . import errors
from . import model
from . import parser

_logger = logging.getLogger(__name__)


class Filter:
    def __init__(
        self,
        *args: typing.Any,
        from_date: Union[None, datetime.date] = None,
        include_inherited_tags: Union[None, bool] = True,
        statuses: Union[None, List[model.Status]] = None,
        tags: Union[None, List[str]] = None,
        to_date: Union[None, datetime.date] = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)

        if include_inherited_tags is None:
            include_inherited_tags = True
        if statuses is None:
            statuses = []
        if tags is None:
            tags = []

        self.from_date = from_date
        self.include_inherited_tags = include_inherited_tags
        self.statuses = statuses
        self.tags = tags
        self.to_date = to_date


class ReportNode:
    def __init__(
        self,
        *args: typing.Any,
        children: Union[None, List["ReportNode"]] = None,
        own_duration: datetime.timedelta,
        task: model.Task,
        total_duration: datetime.timedelta,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        if children is None:
            children = []
        self.children = children
        self.own_duration = own_duration
        self.task = task
        self.total_duration = total_duration


def aggregate(
    task_file: model.TaskFile, filter_: Union[None, Filter] = None
) -> List[ReportNode]:
    if filter_ is None:
        filter_ = Filter()
    filtered = filter_tasks(task_file.tasks, filter_)
    return build_nodes(filtered)


def build_nodes(tasks: List[model.Task]) -> List[ReportNode]:
    nodes = []
    for task in tasks:
        children = build_nodes(task.tasks)
        nodes.append(
            ReportNode(
                task=task,
                own_duration=get_own_duration(task),
                total_duration=task.total_duration(recursive=True),
                children=children,
            ),
        )
    return nodes


def clock_in_range(clock: model.ClockEntry, filter_: Filter) -> bool:
    if filter_.from_date is not None and clock.end is not None:
        if clock.end.date() < filter_.from_date:
            return False
    if filter_.to_date is not None:
        if clock.start.date() > filter_.to_date:
            return False
    return True


def discover_paths(
    files: Union[None, List[str]] = None,
    directory: Union[None, str] = None,
    depth: Union[None, int] = None,
) -> List[pathlib.Path]:
    if not files and directory is None:
        directory = str(xdg.data_home() / "bonipy35" / "taskmd")
    paths = []
    seen = set()

    def add(candidate: pathlib.Path) -> None:
        resolved = pathlib.Path(os.path.realpath(str(candidate)))
        if resolved not in seen:
            seen.add(resolved)
            paths.append(candidate)

    for raw in files or []:
        add(pathlib.Path(raw))

    if directory is not None:
        root = pathlib.Path(directory)
        root_depth = len(pathlib.Path(os.path.realpath(str(root))).parts)
        for candidate in sorted(root.rglob("*")):
            if not candidate.is_file():
                continue
            if depth is not None:
                candidate_depth = (
                    len(
                        pathlib.Path(
                            os.path.realpath(str(candidate))
                        ).parent.parts
                    )
                    - root_depth
                )
                if candidate_depth > depth:
                    continue
            if is_taskmd_path(candidate):
                add(candidate)

    return paths


def filter_tasks(
    tasks: List[model.Task],
    filter_: Filter,
    parent_effective_tags: Union[None, List[str]] = None,
) -> List[model.Task]:
    if parent_effective_tags is None:
        parent_effective_tags = []

    kept = []
    for task in tasks:
        own_effective_tags = task.effective_tags(parent_effective_tags)
        filtered_subtasks = filter_tasks(
            task.tasks, filter_, own_effective_tags
        )
        self_matches = matches_tags(
            task.tags,
            own_effective_tags,
            filter_,
        ) and matches_status(task, filter_)

        if not (self_matches or filtered_subtasks):
            continue

        filtered_clocks = [
            c
            for c in task.clocks
            if self_matches and clock_in_range(c, filter_)
        ]
        task = copy.copy(task)
        task.clocks = filtered_clocks
        task.events = (
            filter_events(task.events, filter_) if self_matches else []
        )
        task.tasks = filtered_subtasks
        kept.append(task)
    return kept


def filter_events(
    events: List[model.Event], filter_: Filter
) -> List[model.Event]:
    filtered = []
    for event in events:
        clone = copy.copy(event)
        clone.clocks = [c for c in event.clocks if clock_in_range(c, filter_)]
        clone.sub_events = filter_events(event.sub_events, filter_)
        filtered.append(clone)
    return filtered


def format_duration(duration: datetime.timedelta) -> str:
    total_seconds = int(duration.total_seconds())
    sign = "-" if total_seconds < 0 else ""
    total_minutes = abs(total_seconds) // 60
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return "{0}{1}h {2:02d}m".format(sign, hours, minutes)
    return "{0}{1}m".format(sign, minutes)


def get_own_duration(task: model.Task) -> datetime.timedelta:
    total = datetime.timedelta(0)
    for clock in task.clocks:
        total += clock.duration()
    for event in task.events:
        for nested_event in event.walk():
            total += nested_event.actual_duration()
    return total


def grand_total(nodes: List[ReportNode]) -> datetime.timedelta:
    total = datetime.timedelta(0)
    for node in nodes:
        total += node.total_duration
    return total


def is_taskmd_path(path: pathlib.Path) -> bool:
    if path.name.endswith(".task.md"):
        return True
    if path.suffix != ".md":
        return False
    try:
        with path.open("r", encoding="utf-8") as handle:
            first_line = handle.readline().rstrip("\n")
    except (OSError, UnicodeDecodeError):
        return False
    return first_line == "<!-- taskmd -->"


def matches_status(task: model.Task, filter_: Filter) -> bool:
    if not filter_.statuses:
        return True
    return task.status in filter_.statuses


def matches_tags(
    own_tags: List[str], effective_tags: List[str], filter_: Filter
) -> bool:
    if not filter_.tags:
        return True
    tags_to_check = (
        effective_tags if filter_.include_inherited_tags else own_tags
    )
    return set(filter_.tags).issubset(set(tags_to_check))


SessionJson = Dict[str, Union[None, str]]
NodeJson = Dict[
    str,
    Union[
        List["NodeJson"],
        List[SessionJson],
        List[str],
        float,
        int,
        str,
    ],
]


def node_to_dict(node: ReportNode, show_sessions: bool) -> NodeJson:
    result = {
        "status": node.task.status.name,
        "title": node.task.title,
        "tags": list(node.task.tags),
        "own_duration_seconds": node.own_duration.total_seconds(),
        "own_duration": format_duration(node.own_duration),
        "total_duration_seconds": node.total_duration.total_seconds(),
        "total_duration": format_duration(node.total_duration),
        "children": [
            node_to_dict(child, show_sessions) for child in node.children
        ],
    }  # type: NodeJson
    if show_sessions:
        result["sessions"] = [
            {
                "start": clock.start.isoformat(),
                "end": clock.end.isoformat() if clock.end else None,
                "description": clock.description,
            }
            for clock in node.task.clocks
        ]
    return result


CSV_FIELDNAMES = [
    "file",
    "level",
    "status",
    "title",
    "tags",
    "own_duration_seconds",
    "total_duration_seconds",
]

NodeCsvRow = Dict[str, Union[float, int, str]]


def node_to_rows(file_label: str, node: ReportNode) -> List[NodeCsvRow]:
    rows = [
        {
            "file": file_label,
            "level": node.task.level,
            "status": node.task.status.name,
            "title": node.task.title,
            "tags": ";".join(node.task.tags),
            "own_duration_seconds": node.own_duration.total_seconds(),
            "total_duration_seconds": node.total_duration.total_seconds(),
        },
    ]  # type: List[NodeCsvRow]
    for child in node.children:
        rows.extend(node_to_rows(file_label, child))
    return rows


def render_csv(sections: List[typing.Tuple[str, List[ReportNode]]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    for file_label, nodes in sections:
        for node in nodes:
            for row in node_to_rows(file_label, node):
                writer.writerow(row)
    return buffer.getvalue()


def render_json(
    sections: List[typing.Tuple[str, List[ReportNode]]],
    show_sessions: bool = False,
) -> str:
    files_payload = []
    overall = datetime.timedelta(0)
    for file_label, nodes in sections:
        total = grand_total(nodes)
        overall += total
        files_payload.append(
            {
                "file": file_label,
                "tasks": [
                    node_to_dict(node, show_sessions) for node in nodes
                ],
                "grand_total_seconds": total.total_seconds(),
                "grand_total": format_duration(total),
            },
        )
    payload = {
        "files": files_payload,
        "grand_total_seconds": overall.total_seconds(),
        "grand_total": format_duration(overall),
    }
    return json.dumps(payload, indent=2)


RULE_WIDTH = 16


def render_multi_text(
    sections: List[typing.Tuple[str, List[ReportNode]]],
    show_sessions: bool = False,
) -> str:
    blocks = []
    overall = datetime.timedelta(0)
    for file_label, nodes in sections:
        blocks.append(render_text(nodes, file_label, show_sessions))
        overall += grand_total(nodes)

    if len(sections) > 1:
        total_label = "Grand total (all files)"
        total_text = format_duration(overall)
        pad = RULE_WIDTH - len(total_label) - len(total_text)
        pad = max(pad, 1)
        blocks.append(
            "{0}\n{1}{2}{3}".format(
                "=" * RULE_WIDTH,
                total_label,
                " " * pad,
                total_text,
            ),
        )
    return "\n\n".join(blocks)


def render_nodes_text(
    nodes: List[ReportNode], indent: int, show_sessions: bool
) -> List[str]:
    lines = []
    for node in nodes:
        lines.append(render_task_line(node, indent))
        if show_sessions:
            lines.extend(render_session_lines(node, indent))
        lines.extend(
            render_nodes_text(node.children, indent + 1, show_sessions)
        )
    return lines


def render_session_lines(node: ReportNode, indent: int) -> List[str]:
    lines = []
    for clock in node.task.clocks:
        span = "{0}--{1}".format(
            datetime_ext.format_datetime(clock.start, minutes=True),
            (
                datetime_ext.format_datetime(clock.end, minutes=True)
                if clock.end
                else "(open)"
            ),
        )
        text = "{0}  {1}".format("  " * (indent + 1), span)
        if clock.description:
            text += " {0}".format(clock.description)
        lines.append(text)
    return lines


def render_task_line(node: ReportNode, indent: int) -> str:
    label = "{0}[{1}] {2}".format(
        "  " * indent, node.task.status.name, node.task.title
    )
    duration_text = format_duration(node.total_duration)
    pad = RULE_WIDTH - len(label) - len(duration_text)
    pad = max(pad, 1)
    return "{0}{1}{2}".format(label, " " * pad, duration_text)


def render_text(
    nodes: List[ReportNode],
    file_label: Union[None, str] = None,
    show_sessions: bool = False,
) -> str:
    lines = []  # type: List[str]
    if file_label is not None:
        lines.append(file_label)
    lines.extend(
        render_nodes_text(nodes, 1 if file_label else 0, show_sessions)
    )
    lines.append("=" * RULE_WIDTH)
    total_label = "Grand total"
    total_text = format_duration(grand_total(nodes))
    pad = RULE_WIDTH - len(total_label) - len(total_text)
    pad = max(pad, 1)
    lines.append("{0}{1}{2}".format(total_label, " " * pad, total_text))
    return "\n".join(lines)


def run(arguments: argparse.Namespace) -> int:
    paths = discover_paths(
        files=(arguments.file or []) + list(arguments.paths),
        directory=arguments.dir,
        depth=arguments.depth,
    )
    if not paths:
        print(
            "taskmd report: no input files given (use --file or --dir)",
            file=sys.stderr,
        )
        return 1

    config = parser.ParseConfig(strict=not arguments.lenient)
    filter_ = Filter(
        from_date=arguments.from_date,
        to_date=arguments.to_date,
        tags=arguments.tag or [],
        statuses=[
            model.Status[status.upper()] for status in arguments.status or []
        ]
        or [],
        include_inherited_tags=not arguments.no_inherited_tags,
    )

    sections = []
    for path in paths:
        try:
            task_file = parser.parse_file(path, config=config)
        except errors.ParseError as error:
            print(
                "taskmd report: {0}: {1}".format(path, error), file=sys.stderr
            )
            return 1
        except OSError as error:
            print(
                "taskmd report: {0}: {1}".format(
                    path, error.strerror or error
                ),
                file=sys.stderr,
            )
            return 1
        nodes = aggregate(task_file, filter_)
        sections.append((str(path), nodes))

    if arguments.format == "json":
        print(render_json(sections, show_sessions=arguments.show_sessions))
    elif arguments.format == "csv":
        print(render_csv(sections), end="")
    else:
        print(
            render_multi_text(sections, show_sessions=arguments.show_sessions)
        )

    return 0


def main(argv: Union[None, List[str]] = None) -> int:
    """Parse report options and run the report command."""
    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)
    argument_parser = argparse.ArgumentParser(
        description="summarize tracked time across one or more taskmd files",
    )
    logging_ext.add_verbose_flag(argument_parser)
    cli_args.add_input_flags(argument_parser)
    argument_parser.add_argument(
        "--from",
        dest="from_date",
        type=cli_args.parse_iso_date,
        metavar="DATE",
        help="only count clock sessions ending on or after DATE",
    )
    argument_parser.add_argument(
        "--to",
        dest="to_date",
        type=cli_args.parse_iso_date,
        metavar="DATE",
        help="only count clock sessions starting on or before DATE",
    )
    argument_parser.add_argument(
        "--tag",
        action="append",
        dest="tag",
        metavar="TAG",
        help="only include tasks carrying TAG (repeatable; all must match)",
    )
    cli_args.add_status_flag(
        argument_parser,
        help_text="only include tasks with this status (repeatable)",
    )
    cli_args.add_mode_flags(argument_parser)
    argument_parser.add_argument(
        "--format",
        choices=("text", "json", "csv"),
        default="text",
        help="output format (default: text)",
    )
    argument_parser.add_argument(
        "--show-sessions",
        action="store_true",
        help="expand each task to list its individual clock sessions",
    )
    argument_parser.add_argument(
        "--no-inherited-tags",
        action="store_true",
        help="disable tag inheritance when matching --tag filters",
    )

    arguments = argument_parser.parse_args(argv[1:])
    return run(arguments)


if __name__ == "__main__":
    sys.exit(main())
