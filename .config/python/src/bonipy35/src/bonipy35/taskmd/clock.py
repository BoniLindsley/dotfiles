#!/usr/bin/env python3

# Standard libraries.
import argparse
import datetime
import json
import logging
import pathlib
import sys
import typing

from typing import List, Tuple, Union

# Internal modules.
from .. import datetime_ext
from .. import logging_ext

from . import cli_args
from . import errors
from . import model
from . import parser

_logger = logging.getLogger(__name__)


def parse_iso_datetime(value: str) -> datetime.datetime:
    try:
        parsed = parser.parse_datetime(
            value, config=parser.ParseConfig(), line_number=0
        )
    except errors.ParseError as error:
        raise argparse.ArgumentTypeError(
            "{0!r} is not a valid ISO-8601 datetime".format(value),
        ) from error
    return parsed


class ControlError(errors.TaskmdError):
    pass


class TaskNotFoundError(ControlError):
    pass


class AmbiguousTaskError(ControlError):
    pass


class AlreadyOpenError(ControlError):
    pass


class NoOpenSessionError(ControlError):
    pass


class AmbiguousOpenSessionError(ControlError):
    def __init__(
        self,
        message: object,
        open_sessions: List[Tuple[model.Task, model.ClockEntry]],
    ):
        super().__init__(message)
        self.open_sessions = open_sessions


# ---------------------------------------------------------------------------
# Locating a task by line number or title
# ---------------------------------------------------------------------------


class Bound:
    def __init__(
        self,
        *args: typing.Any,
        end_line: int,
        start_line: int,
        task: model.Task,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.end_line = end_line
        self.start_line = start_line
        self.task = task


def compute_bounds(task_file: model.TaskFile) -> List[Bound]:
    flat = list(task_file.walk())
    headings = sorted(
        flat + list(task_file.walk_events()),
        key=lambda node: node.source_line,
    )
    bounds = []
    for task in flat:
        end_line = 0
        for later in headings:
            if (
                later.source_line > task.source_line
                and later.level <= task.level
            ):
                end_line = later.source_line
                break
        if not end_line and task_file.total_lines:
            end_line = task_file.total_lines + 1
        bounds.append(
            Bound(task=task, start_line=task.source_line, end_line=end_line)
        )
    return bounds


def find_task_at_line(
    task_file: model.TaskFile, line: int
) -> Union[None, model.Task]:
    """Return the innermost task whose range contains `line`, or
    `None` if no task's range contains it.

    Because task ranges nest (a subtask's range is always inside its
    parent's), the innermost match is simply the one with the greatest
    `level` among every task whose range contains `line`.
    """
    matches = [
        bound
        for bound in compute_bounds(task_file)
        if bound.start_line <= line < bound.end_line
    ]
    if not matches:
        return None
    matches.sort(key=lambda bound: (bound.task.level, bound.start_line))
    return matches[-1].task


def find_task_by_title(task_file: model.TaskFile, title: str) -> model.Task:
    """Return the single task whose title exactly matches `title`.

    Raises `TaskNotFoundError` if none match, or
    `AmbiguousTaskError` if more than one does.
    """
    matches = [task for task in task_file.walk() if task.title == title]
    if not matches:
        raise TaskNotFoundError(
            "no task titled {0!r}".format(title),
        )
    if len(matches) > 1:
        raise AmbiguousTaskError(
            "{0} tasks are titled {1!r}; use --line instead".format(
                len(matches),
                title,
            ),
        )
    return matches[0]


def resolve_task(
    task_file: model.TaskFile,
    line: Union[None, int],
    task_title: Union[None, str],
) -> model.Task:
    """Shared locator logic for `clock_start`/`clock_status`: resolve
    exactly one of `line` / `task_title` to a `Task`."""
    if task_title is not None:
        if line is not None:
            raise ValueError("pass only one of line or task_title")
        return find_task_by_title(task_file, task_title)
    if line is None:
        raise ValueError("pass one of line or task_title")
    task = find_task_at_line(task_file, line)
    if task is None:
        raise TaskNotFoundError(
            "no task found at line {0}".format(line),
        )
    return task


def task_breadcrumb(task_file: model.TaskFile, target: model.Task) -> str:
    path = []

    def _search(tasks: List[model.Task], trail: List[str]) -> bool:
        for task in tasks:
            new_trail = trail + [task.title]
            if task is target:
                path.extend(new_trail)
                return True
            if _search(task.tasks, new_trail):
                return True
        return False

    _search(task_file.tasks, [])
    return " > ".join(path) if path else target.title


# ---------------------------------------------------------------------------
# Surgical line-level rewriting
# ---------------------------------------------------------------------------


class LineRewriter:
    """An in-memory, line-level editor for a `taskmd` file's raw text.

    Operates on 1-based line numbers, matching `Task.source_line` and
    friends. Editing methods mutate `self.lines` directly; nothing
    touches disk until `write_atomic` is called.
    """

    def __init__(self, text: str) -> None:
        self.lines = text.splitlines(keepends=True)
        self.newline = "\n"
        for line in self.lines:
            if line.endswith("\r\n"):
                self.newline = "\r\n"
                break
            if line.endswith("\n") or line.endswith("\r"):
                self.newline = line[-1:]
                break

    def replace_line(self, line_number: int, new_text: str) -> None:
        """Replace the 1-based line `line_number` with `new_text`."""
        original = self.lines[line_number - 1]
        ending = original[len(original.rstrip("\r\n")) :]
        self.lines[line_number - 1] = new_text + ending

    def insert_before(self, line_number: int, new_lines: List[str]) -> None:
        """Insert `new_lines` immediately before the 1-based line
        `line_number` (or at the end of the file if `line_number` is
        one past the last line)."""
        index = line_number - 1
        # An append must terminate the former last line to keep headings
        # separate; all other existing bytes, including mixed endings, stay.
        if index == len(self.lines) and self.lines:
            if not self.lines[-1].endswith(("\r", "\n")):
                self.lines[-1] += self.newline
        self.lines[index:index] = [line + self.newline for line in new_lines]

    def render(self) -> str:
        return "".join(self.lines)

    def write_atomic(self, path: pathlib.Path) -> None:
        """Write the current contents to `path` atomically: write to
        `path.name + ".tmp"` first, then rename over the original, so
        a crash mid-write can never leave `path` truncated or
        half-written."""
        path = pathlib.Path(path)
        tmp_path = path.with_name(path.name + ".tmp")
        tmp_path.write_bytes(self.render().encode("utf-8"))
        tmp_path.replace(path)


# ---------------------------------------------------------------------------
# Formatting a CLOCK: heading line
# ---------------------------------------------------------------------------


def _format_datetime(value: datetime.datetime) -> str:
    return datetime_ext.format_datetime(value)


def _clock_heading_depth(task: model.Task) -> int:
    return task.level + 1


def _format_clock_heading(
    depth: int,
    start: datetime.datetime,
    end: Union[None, datetime.datetime],
    description: str,
) -> str:
    prefix = "{0} CLOCK: [{1}]--".format("#" * depth, _format_datetime(start))
    if end is not None:
        prefix += "[{0}]".format(_format_datetime(end))
    if description:
        prefix += " {0}".format(description)
    return prefix


# ---------------------------------------------------------------------------
# clock start
# ---------------------------------------------------------------------------


def clock_start(  # pylint: disable=too-many-arguments
    path: pathlib.Path,
    config: Union[None, parser.ParseConfig] = None,
    *,
    line: Union[None, int] = None,
    task_title: Union[None, str] = None,
    note: Union[None, str] = None,
    now: Union[None, datetime.datetime] = None
) -> model.ClockEntry:
    """Append a new open `CLOCK:` entry to the task at `line` (or
    titled `task_title`) in the file at `path`, and write the file.

    Raises `AlreadyOpenError` in strict mode if that task
    already has an unclosed session (lenient mode allows stacking
    multiple open sessions on one task, per SPEC.md section 5's
    "Unclosed CLOCK:" row treating this as ordinary, not exceptional).
    Returns the newly created `ClockEntry` (with its `source_line` set
    to where it was written) for confirmation or testing.
    """
    if config is None:
        config = parser.ParseConfig()
    if now is None:
        now = datetime.datetime.now(config.local_timezone)

    task_file = parser.parse_file(path, config=config)
    task = resolve_task(task_file, line, task_title)

    if config.strict and any(clock.is_open() for clock in task.clocks):
        raise AlreadyOpenError(
            "task {0!r} already has an open CLOCK: session".format(
                task.title,
            ),
        )

    depth = _clock_heading_depth(task)
    heading_text = _format_clock_heading(depth, now, None, note or "")

    insertion_line = task.tasks[0].source_line if task.tasks else None
    if insertion_line is None:
        bound = next(b for b in compute_bounds(task_file) if b.task is task)
        insertion_line = bound.end_line

    rewriter = LineRewriter(path.read_bytes().decode("utf-8"))
    rewriter.insert_before(insertion_line, [heading_text])
    rewriter.write_atomic(path)

    return model.ClockEntry(
        start=now,
        end=None,
        description=note or "",
        work_notes="",
        source_line=insertion_line,
    )


# ---------------------------------------------------------------------------
# clock stop
# ---------------------------------------------------------------------------


def list_open_clocks(
    task_file: model.TaskFile,
) -> List[Tuple[model.Task, model.ClockEntry]]:
    """Every open `CLOCK:` entry in the file, as `(task, clock)`
    pairs, in document order."""
    return [
        (task, clock)
        for task in task_file.walk()
        for clock in task.clocks
        if clock.is_open()
    ]


def _find_stop_target(
    task_file: model.TaskFile, line: Union[None, int]
) -> Tuple[model.Task, model.ClockEntry]:
    if line is not None:
        task = find_task_at_line(task_file, line)
        if task is None:
            raise TaskNotFoundError(
                "no task found at line {0}".format(line),
            )
        open_clocks = [c for c in task.clocks if c.is_open()]
        if not open_clocks:
            raise NoOpenSessionError(
                "task {0!r} has no open CLOCK: session".format(task.title),
            )
        return task, open_clocks[0]

    open_sessions = list_open_clocks(task_file)
    if not open_sessions:
        raise NoOpenSessionError("no open CLOCK: session in file")
    if len(open_sessions) > 1:
        raise AmbiguousOpenSessionError(
            "{0} open CLOCK: sessions found; specify --line".format(
                len(open_sessions),
            ),
            open_sessions,
        )
    return open_sessions[0]


def clock_stop(
    path: pathlib.Path,
    config: Union[None, parser.ParseConfig] = None,
    *,
    line: Union[None, int] = None,
    note: Union[None, str] = None,
    at: Union[None, datetime.datetime] = None
) -> model.ClockEntry:
    """Close an open `CLOCK:` entry and write the file.

    If `line` is omitted, the single open session in the file is
    closed; if there are zero or more than one, raises
    `NoOpenSessionError` / `AmbiguousOpenSessionError`
    (the latter carrying every open `(task, clock)` pair so the caller
    can disambiguate). If `note` is given, it replaces the heading
    line's description (work notes in the body below are untouched).
    Returns the closed `ClockEntry`.
    """
    if config is None:
        config = parser.ParseConfig()
    if at is None:
        at = datetime.datetime.now(config.local_timezone)

    task_file = parser.parse_file(path, config=config)
    task, clock = _find_stop_target(task_file, line)

    description = note if note is not None else clock.description
    depth = _clock_heading_depth(task)
    heading_text = _format_clock_heading(depth, clock.start, at, description)

    rewriter = LineRewriter(path.read_bytes().decode("utf-8"))
    rewriter.replace_line(clock.source_line, heading_text)
    rewriter.write_atomic(path)

    return model.ClockEntry(
        start=clock.start,
        end=at,
        description=description,
        work_notes=clock.work_notes,
        source_line=clock.source_line,
    )


# ---------------------------------------------------------------------------
# clock status
# ---------------------------------------------------------------------------


def clock_status(
    task_file: model.TaskFile, line: Union[None, int] = None
) -> int:
    """Exit-code-style status check: `0` = an open session exists
    (for the task at `line`, or anywhere in the file if `line` is
    omitted); `1` = none is open; `2` = `line` was given but no task
    was found there."""
    if line is None:
        return 0 if list_open_clocks(task_file) else 1
    task = find_task_at_line(task_file, line)
    if task is None:
        return 2
    return 0 if any(clock.is_open() for clock in task.clocks) else 1


def _clock_config(args: argparse.Namespace) -> parser.ParseConfig:
    return parser.ParseConfig(strict=not args.lenient)


def _run_clock_start(args: argparse.Namespace) -> int:
    config = _clock_config(args)
    try:
        clock = clock_start(
            args.path,
            config,
            line=args.line,
            task_title=args.task_title,
            note=args.note,
        )
    except (errors.ParseError, ControlError, OSError) as error:
        print("taskmd clock start: {0}".format(error), file=sys.stderr)
        return 1
    print(
        "started clock at {0} (line {1})".format(
            datetime_ext.format_datetime(clock.start),
            clock.source_line,
        ),
    )
    return 0


def _run_clock_stop(args: argparse.Namespace) -> int:
    config = _clock_config(args)
    try:
        clock = clock_stop(
            args.path,
            config,
            line=args.line,
            note=args.note,
            at=args.time,
        )
    except AmbiguousOpenSessionError as error:
        print("taskmd clock stop: {0}".format(error), file=sys.stderr)
        task_file = parser.parse_file(args.path, config=config)
        for task, open_clock in error.open_sessions:
            print(
                "  line {0}: {1} (started {2})".format(
                    open_clock.source_line,
                    task_breadcrumb(task_file, task),
                    datetime_ext.format_datetime(open_clock.start),
                ),
                file=sys.stderr,
            )
        return 2
    except (errors.ParseError, ControlError, OSError) as error:
        print("taskmd clock stop: {0}".format(error), file=sys.stderr)
        return 1
    end = clock.end
    assert end
    print(
        "stopped clock: {0} -- {1} (line {2})".format(
            datetime_ext.format_datetime(clock.start),
            datetime_ext.format_datetime(end),
            clock.source_line,
        ),
    )
    return 0


def _run_clock_list_open(args: argparse.Namespace) -> int:
    config = _clock_config(args)
    try:
        task_file = parser.parse_file(args.path, config=config)
    except errors.ParseError as error:
        print("taskmd clock list-open: {0}".format(error), file=sys.stderr)
        return 1
    except OSError as error:
        print("taskmd clock list-open: {0}".format(error), file=sys.stderr)
        return 1
    payload = [
        {
            "task": task_breadcrumb(task_file, task),
            "line": open_clock.source_line,
            "start": datetime_ext.format_datetime(open_clock.start),
            "description": open_clock.description,
        }
        for task, open_clock in list_open_clocks(task_file)
    ]
    print(json.dumps(payload, indent=2))
    return 0


def _run_clock_status(args: argparse.Namespace) -> int:
    config = _clock_config(args)
    try:
        task_file = parser.parse_file(args.path, config=config)
    except errors.ParseError as error:
        print("taskmd clock status: {0}".format(error), file=sys.stderr)
        return 1
    except OSError as error:
        print("taskmd clock status: {0}".format(error), file=sys.stderr)
        return 1
    code = clock_status(task_file, line=args.line)
    print(("open", "closed", "task not found")[code])
    return code


def run(args: argparse.Namespace) -> int:
    if args.clock_command is None:
        print(
            "taskmd clock: choose a subcommand (start/stop/list-open/status)",
            file=sys.stderr,
        )
        return 1
    handlers = {
        "start": _run_clock_start,
        "stop": _run_clock_stop,
        "list-open": _run_clock_list_open,
        "status": _run_clock_status,
    }
    return handlers[args.clock_command](args)


def main(argv: Union[None, List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    argument_parser = argparse.ArgumentParser(
        description="start/stop time-tracking sessions in a taskmd file",
    )
    logging_ext.add_verbose_flag(argument_parser)

    clock_subparsers = argument_parser.add_subparsers(dest="clock_command")

    start_parser = clock_subparsers.add_parser(
        "start",
        help="open a new CLOCK: session on a task",
    )
    start_parser.add_argument(
        "path", help="the .task.md file to edit", type=pathlib.Path
    )
    locator_group = start_parser.add_mutually_exclusive_group(required=True)
    locator_group.add_argument(
        "--line",
        type=int,
        metavar="LINE",
        help="line number identifying the target task",
    )
    locator_group.add_argument(
        "--task-title",
        metavar="TITLE",
        help="exact title of the target task",
    )
    start_parser.add_argument(
        "--note",
        metavar="TEXT",
        help="description for the CLOCK: heading",
    )
    cli_args.add_mode_flags(start_parser)

    stop_parser = clock_subparsers.add_parser(
        "stop",
        help="close an open CLOCK: session",
    )
    stop_parser.add_argument(
        "path", help="the .task.md file to edit", type=pathlib.Path
    )
    stop_parser.add_argument(
        "--line",
        type=int,
        metavar="LINE",
        help="line number identifying the target task "
        "(omit to close the file's single open session)",
    )
    stop_parser.add_argument(
        "--note",
        metavar="TEXT",
        help="replace the CLOCK: heading's description",
    )
    stop_parser.add_argument(
        "--time",
        dest="time",
        type=parse_iso_datetime,
        metavar="DATETIME",
        help="end time to record (default: now); must include a "
        "timezone offset",
    )
    cli_args.add_mode_flags(stop_parser)

    list_open_parser = clock_subparsers.add_parser(
        "list-open",
        help="list every unclosed CLOCK: session (as JSON)",
    )
    list_open_parser.add_argument("path", help="the .task.md file to read")
    cli_args.add_mode_flags(list_open_parser)

    status_parser = clock_subparsers.add_parser(
        "status",
        help="check for an open session; exit 0=open, 1=closed, "
        "2=task not found",
    )
    status_parser.add_argument("path", help="the .task.md file to read")
    status_parser.add_argument(
        "--line",
        type=int,
        metavar="LINE",
        help="line number identifying the target task "
        "(omit to check the whole file)",
    )
    cli_args.add_mode_flags(status_parser)

    arguments = argument_parser.parse_args(argv[1:])

    return run(arguments)


if __name__ == "__main__":
    sys.exit(main())
