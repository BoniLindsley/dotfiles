#!/usr/bin/env python3

# Need Python 3.5 support.
# pylint: disable=consider-using-f-string

# Standard libraries.
import argparse
import datetime
import logging
import sys

from typing import List, Union

# Internal modules.
from .. import logging_ext

from . import errors
from . import model
from . import parser
from . import report

_logger = logging.getLogger(__name__)


def parse_iso_date(value: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "{0!r} is not a valid ISO-8601 date (expected YYYY-MM-DD)".format(
                value,
            ),
        ) from error


def run_report(arguments: argparse.Namespace) -> int:
    paths = report.discover_paths(
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
    filter_ = report.Filter(
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
        nodes = report.aggregate(task_file, filter_)
        sections.append((str(path), nodes))

    if arguments.format == "json":
        print(
            report.render_json(
                sections, show_sessions=arguments.show_sessions
            )
        )
    elif arguments.format == "csv":
        print(report.render_csv(sections), end="")
    else:
        print(
            report.render_multi_text(
                sections, show_sessions=arguments.show_sessions
            )
        )

    return 0


def main(argv: Union[None, List[str]] = None) -> int:

    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    argument_parser = argparse.ArgumentParser(
        description="Markdown-based hierarchical task and time-tracking tool.",
    )
    logging_ext.add_verbose_flag(argument_parser)

    subparsers = argument_parser.add_subparsers(dest="command")

    report_parser = subparsers.add_parser(
        "report",
        help="summarize tracked time across one or more taskmd files",
    )
    report_parser.add_argument(
        "paths",
        nargs="*",
        help="taskmd file(s) to read, in addition to any --file/--dir",
    )
    report_parser.add_argument(
        "--file",
        action="append",
        dest="file",
        metavar="FILE",
        help="an explicit file to read (repeatable)",
    )
    report_parser.add_argument(
        "--dir",
        dest="dir",
        metavar="DIR",
        help="recursively scan DIR for .task.md files",
    )
    report_parser.add_argument(
        "--depth",
        type=int,
        default=None,
        metavar="N",
        help="limit recursive directory depth (only with --dir)",
    )
    report_parser.add_argument(
        "--from",
        dest="from_date",
        type=parse_iso_date,
        metavar="DATE",
        help="only count clock sessions ending on or after DATE",
    )
    report_parser.add_argument(
        "--to",
        dest="to_date",
        type=parse_iso_date,
        metavar="DATE",
        help="only count clock sessions starting on or before DATE",
    )
    report_parser.add_argument(
        "--tag",
        action="append",
        dest="tag",
        metavar="TAG",
        help="only include tasks carrying TAG (repeatable; all must match)",
    )
    report_parser.add_argument(
        "--status",
        action="append",
        dest="status",
        choices=list(status.name for status in model.Status),
        metavar="STATUS",
        help="only include tasks with this status (repeatable)",
    )
    mode_group = report_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--strict",
        action="store_true",
        help="strict parsing (default)",
    )
    mode_group.add_argument(
        "--lenient",
        action="store_true",
        help="lenient parsing",
    )
    report_parser.add_argument(
        "--format",
        choices=("text", "json", "csv"),
        default="text",
        help="output format (default: text)",
    )
    report_parser.add_argument(
        "--show-sessions",
        action="store_true",
        help="expand each task to list its individual clock sessions",
    )
    report_parser.add_argument(
        "--no-inherited-tags",
        action="store_true",
        help="disable tag inheritance when matching --tag filters",
    )

    subparsers.add_parser("clock")
    subparsers.add_parser("schedule")

    arguments = argument_parser.parse_args(argv[1:])

    command = arguments.command
    if command == "clock":
        # Implement in phase 4.
        _logger.error("Unimplemented command: %s", command)
        return 1
    if command == "report":
        return run_report(arguments)
    if command == "schedule":
        # Implement in phase 6.
        _logger.error("Unimplemented command: %s", command)
        return 1

    _logger.error("Unknown command: %s", command)
    return 1


if __name__ == "__main__":
    sys.exit(main())
