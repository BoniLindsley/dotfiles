#!/usr/bin/env python3
"""One-shot commands and live notification watching."""

# Standard libraries.
import argparse
import datetime
import re
import sys
import time
import typing

from typing import Dict, List, Union

# Internal modules.
from . import client, data, paths

_DURATION = re.compile(
    r"\s*(?:(?P<days>[0-9]+)d)?\s*(?:(?P<hours>[0-9]+)h)?"
    r"\s*(?:(?P<minutes>[0-9]+)m)?\s*(?:(?P<seconds>[0-9]+)s)?\s*\Z"
)


def parse_duration(value: str) -> datetime.timedelta:
    match = _DURATION.match(value)
    if match is None:
        raise ValueError("Expected a duration such as 1h30m or 45s")
    duration = datetime.timedelta(
        days=int(match.group("days") or 0),
        hours=int(match.group("hours") or 0),
        minutes=int(match.group("minutes") or 0),
        seconds=int(match.group("seconds") or 0),
    )
    if duration <= datetime.timedelta():
        raise ValueError("Duration must be positive")
    return duration


def parse_alarm_time(value: str, now: datetime.datetime) -> datetime.datetime:
    local_now = now.astimezone()
    try:
        naive = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            clock_time = datetime.datetime.strptime(value, "%H:%M").time()
        except ValueError as error:
            raise ValueError("Expected HH:MM or YYYY-MM-DD HH:MM") from error
        naive = datetime.datetime.combine(local_now.date(), clock_time)
        if naive < local_now.replace(tzinfo=None):
            naive += datetime.timedelta(days=1)
    # mktime can silently normalize nonexistent times or choose one side of a
    # DST fold. Enumerate both DST choices and require a unique round trip.
    candidates = set()
    for daylight_saving in (0, 1):
        fields = naive.timetuple()[:8] + (daylight_saving,)
        timestamp = time.mktime(fields)
        if datetime.datetime.fromtimestamp(timestamp) == naive:
            candidates.add(timestamp)
    if len(candidates) != 1:
        raise ValueError("Local time is ambiguous or nonexistent")
    return datetime.datetime.fromtimestamp(
        candidates.pop(), datetime.timezone.utc
    )


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    paths.add_directory_argument(parser)
    commands = parser.add_subparsers(dest="command")
    alarm = commands.add_parser("alarm")
    alarm.add_argument("end_time")
    alarm.add_argument("--name", default="")
    timer = commands.add_parser("timer")
    timer.add_argument("duration")
    timer.add_argument("--name", default="")
    reschedule = commands.add_parser("reschedule")
    reschedule.add_argument("id_", type=int)
    reschedule.add_argument("end_time")
    for name in ("delete", "pause", "resume", "stop", "restart", "dismiss"):
        commands.add_parser(name).add_argument("id_", type=int)
    for name in ("status", "notifications", "watch", "shutdown"):
        commands.add_parser(name)
    return parser


def request_fields(arguments: argparse.Namespace) -> Dict[str, typing.Any]:
    fields = {}  # type: Dict[str, typing.Any]
    if arguments.command in ("alarm", "reschedule"):
        fields["end_time"] = data.Datetime.model_dump(
            parse_alarm_time(arguments.end_time, data.utc_now())
        )
    elif arguments.command == "timer":
        fields["duration"] = parse_duration(
            arguments.duration
        ).total_seconds()
    if hasattr(arguments, "id_"):
        fields["id_"] = arguments.id_
    if hasattr(arguments, "name"):
        fields["name"] = arguments.name
    return fields


def format_snapshot(snapshot: client.Snapshot) -> List[str]:
    lines = []
    for item in snapshot["items"]:
        lines.append(
            "{id_}: {name} | {state} | {notification_state} | remaining {remaining:g}s | {end_time}".format(
                **item
            )
        )
    for notification in snapshot["notifications"]:
        lines.append(
            "Notification {id_}: {name} ({kind})".format(
                kind=notification["notification_state"], **notification
            )
        )
    return lines


def display(snapshot: client.Snapshot) -> None:
    for line in format_snapshot(snapshot):
        print(line)


def main(argv: Union[None, List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv
    parser = make_parser()
    arguments = parser.parse_args(argv[1:])
    if arguments.command is None:
        parser.print_help()
        return 1
    try:
        # Validate input before starting a service.
        fields = request_fields(arguments)
        with client.Client(directory=arguments.directory) as connection:
            if arguments.command == "watch":
                display(connection.snapshot)
                with connection.events():
                    while True:
                        connection.receive()
                        display(connection.snapshot)
            display(connection.request(arguments.command, **fields))
    except KeyboardInterrupt:
        return 0
    except (
        OSError,
        ValueError,
        RuntimeError,
        EOFError,
        OverflowError,
    ) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
